"""Read-only Java/Fabric migration evidence; never executes or translates code.

Only local archive entries are read. Declared nested jars are inspected in memory.
Limits and omitted coverage are part of the returned JSON report.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import zipfile
import zlib

MAX_ENTRIES = 10000
MAX_MEMBER = 2 * 1024 * 1024
MAX_JSON = 512 * 1024
MAX_READ = 64 * 1024 * 1024
MAX_HASH = 1024 * 1024 * 1024
MAX_NESTED_MEMBER = 16 * 1024 * 1024
MAX_NESTED_DEPTH = 4
MAX_CLASSES = 1000
MAX_EVIDENCE = 2000
READ_ERRORS = (OSError, ValueError, RuntimeError, NotImplementedError,
               zipfile.BadZipFile, EOFError, zlib.error, lzma.LZMAError)


def _safe_name(name):
    return (bool(name) and not name.startswith('/') and '\\' not in name
            and ':' not in name and '..' not in PurePosixPath(name).parts)


class _Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, count):
        if count < 0 or self.pos + count > len(self.data):
            raise ValueError('truncated class file')
        value = self.data[self.pos:self.pos + count]
        self.pos += count
        return value

    def u1(self):
        return self.take(1)[0]

    def u2(self):
        return struct.unpack('>H', self.take(2))[0]

    def u4(self):
        return struct.unpack('>I', self.take(4))[0]


def _class_evidence(data):
    """Parse constant-pool references and declaration annotations, not bytecode.

    Constant-pool references show a symbolic dependency, not proof a call runs.
    Unknown attributes (including Code) are skipped by their declared length.
    """
    r = _Reader(data)
    if r.take(4) != b'\xca\xfe\xba\xbe':
        raise ValueError('invalid class magic')
    minor, major = r.u2(), r.u2()
    count = r.u2()
    cp = [None] * count
    i = 1
    while i < count:
        tag = r.u1()
        if tag == 1:
            cp[i] = (tag, r.take(r.u2()).decode('utf-8', errors='replace'))
        elif tag in (3, 4):
            cp[i] = (tag, r.take(4).hex())
        elif tag in (5, 6):
            cp[i] = (tag, r.take(8).hex())
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = (tag, r.u2())
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[i] = (tag, r.u2(), r.u2())
        elif tag == 15:
            cp[i] = (tag, r.u1(), r.u2())
        else:
            raise ValueError('unknown constant-pool tag %s' % tag)
        i += 1

    def item(index, tag=None):
        if not 0 < index < count or cp[index] is None:
            raise ValueError('invalid constant-pool index')
        value = cp[index]
        if tag is not None and value[0] != tag:
            raise ValueError('unexpected constant-pool type')
        return value

    def utf(index):
        return item(index, 1)[1]

    def annotation(ar, depth=0):
        if depth > 24:
            raise ValueError('annotation nesting limit')
        desc = utf(ar.u2())
        values = {}
        for _ in range(ar.u2()):
            key = utf(ar.u2())
            values[key] = element(ar, depth + 1)
        return {'type': desc, 'values': values}

    def element(ar, depth):
        if depth > 24:
            raise ValueError('annotation nesting limit')
        tag = chr(ar.u1())
        if tag in 'BCDFIJSZs':
            return item(ar.u2())[1]
        if tag == 'c':
            return {'class': utf(ar.u2())}
        if tag == 'e':
            return {'enum': utf(ar.u2()), 'value': utf(ar.u2())}
        if tag == '@':
            return annotation(ar, depth + 1)
        if tag == '[':
            return [element(ar, depth + 1) for _ in range(ar.u2())]
        raise ValueError('unknown annotation value tag')

    annotations = []

    def attributes(owner):
        for _ in range(r.u2()):
            name = utf(r.u2())
            body = r.take(r.u4())
            if name in ('RuntimeVisibleAnnotations', 'RuntimeInvisibleAnnotations'):
                ar = _Reader(body)
                for _ in range(ar.u2()):
                    value = annotation(ar)
                    if ('org/spongepowered/asm/mixin/' in value['type']
                            or 'com/llamalad7/mixinextras/' in value['type']):
                        annotations.append({'declaration': owner, **value})

    r.u2()
    class_name = utf(item(r.u2(), 7)[1])
    r.u2()
    r.take(r.u2() * 2)
    for kind in ('field', 'method'):
        for _ in range(r.u2()):
            r.u2()
            name, descriptor = utf(r.u2()), utf(r.u2())
            attributes('%s %s%s' % (kind, name, descriptor))
    attributes('class ' + class_name)
    refs = []
    for value in cp[1:]:
        if value and value[0] in (9, 10, 11):
            owner = utf(item(value[1], 7)[1])
            nt = item(value[2], 12)
            refs.append({'kind': 'field' if value[0] == 9 else 'method',
                         'owner': owner, 'name': utf(nt[1]), 'descriptor': utf(nt[2])})
    return {'name': class_name, 'major_version': major, 'minor_version': minor,
            'references': sorted(refs, key=lambda x: tuple(x.values())),
            'mixin_annotations': annotations}


def analyze_mod(path: Path) -> dict:
    """Return deterministic evidence with one shared expansion budget per input."""
    state = {'bytes_read': 0, 'cache': {}, 'inspected': 0, 'cache_hits': 0}
    report = _analyze_mod(Path(path), state, 0, [str(path)])
    report['coverage']['total_bytes_read'] = state['bytes_read']
    report['coverage']['nested_stats'] = {
        'archives_inspected': state['inspected'], 'cache_hits': state['cache_hits'],
        'unique_hashes': len(state['cache'])}
    return report


def _rechain(report, chain):
    """Give cached evidence its current occurrence's provenance."""
    old_chain = report['archive_chain']
    report['archive_chain'] = chain
    report['path'] = '!/'.join(chain)
    for nested in report['nested_jars']:
        nested['archive_chain'] = chain + nested['archive_chain'][len(old_chain):]
        if nested.get('report'):
            _rechain(nested['report'], nested['archive_chain'])
    return report


def _analyze_mod(path, state, depth, chain, data=None):
    path = Path(path)
    report = {'schema_version': 1, 'path': '!/'.join(chain), 'name': path.name,
              'id': None, 'version': None, 'sha256': None, 'archive_chain': chain,
              'kind': 'directory' if data is None and path.is_dir() else 'jar', 'fabric': None,
              'mixins': [], 'nested_jars': [], 'classes': [],
              'content': {'assets': 0, 'data': 0, 'classes': 0, 'patterns': {}},
              'findings': [], 'mapping': [], 'porting_tasks': [],
              'coverage': {'complete': True, 'incomplete': False, 'nested_jars_inspected': True,
                           'limits': {'nested_depth': MAX_NESTED_DEPTH,
                                      'nested_member_bytes': MAX_NESTED_MEMBER,
                                      'total_read_bytes': MAX_READ,
                                      'entries_per_archive': MAX_ENTRIES,
                                      'classes_per_archive': MAX_CLASSES},
                           'bytes_read': 0, 'classes_inspected': 0, 'limitations': []}}
    coverage = report['coverage']

    def limited(reason):
        coverage['complete'] = False
        coverage['incomplete'] = True
        if reason not in coverage['limitations']:
            coverage['limitations'].append(reason)

    def finding(severity, source, evidence, reason, action, status='review', code=None):
        if len(report['findings']) >= MAX_EVIDENCE:
            limited('finding limit reached')
            return
        report['findings'].append({'code': code or status, 'severity': severity, 'source_entry': source,
                                   'evidence': evidence, 'reason': reason,
                                   'next_action': action, 'manual_next_action': action, 'mapping_status': status})

    archive = None
    entries = {}
    declared_nested = set()
    try:
        if data is None and path.is_symlink():
            raise ValueError('input symlinks are not followed')
        if data is None and path.is_dir():
            stopped = False
            for root, dirs, files in os.walk(path, followlinks=False):
                if any((Path(root) / d).is_symlink() for d in dirs):
                    limited('directory symlinks skipped')
                dirs[:] = sorted(d for d in dirs if not (Path(root) / d).is_symlink())
                for name in sorted(files):
                    member = Path(root) / name
                    rel = member.relative_to(path).as_posix()
                    if member.is_symlink():
                        limited('directory symlinks skipped')
                        continue
                    if not _safe_name(rel) or not member.is_file():
                        limited('unsafe or nonregular directory entries skipped')
                        continue
                    entries[rel] = member
                    if len(entries) >= MAX_ENTRIES:
                        limited('entry limit reached')
                        stopped = True
                        break
                if stopped:
                    break
        else:
            archive = zipfile.ZipFile(io.BytesIO(data) if data is not None else path)
            for info in archive.infolist()[:MAX_ENTRIES]:
                if info.is_dir():
                    continue
                if (not _safe_name(info.filename)
                        or stat.S_ISLNK(info.external_attr >> 16)):
                    limited('unsafe archive entries skipped')
                    finding('warning', info.filename, 'unsafe entry path or symlink',
                            'Entry cannot be used as a local resource.', 'Remove the unsafe entry.')
                    continue
                if info.filename in entries:
                    limited('duplicate archive entries skipped')
                    continue
                entries[info.filename] = info
            if len(archive.infolist()) > MAX_ENTRIES:
                limited('entry limit reached')

        digest = hashlib.sha256()
        hashed = 0
        hash_inputs = [] if data is not None else ([(None, path)] if archive else sorted(entries.items()))
        if data is not None:
            digest.update(data)
        for name, item_path in hash_inputs:
            if name is not None:
                digest.update(name.encode('utf-8') + b'\0')
                digest.update(str(item_path.stat().st_size).encode('ascii') + b'\0')
            with item_path.open('rb') as stream:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    hashed += len(chunk)
                    if hashed > MAX_HASH:
                        raise ValueError('hash byte limit exceeded')
                    digest.update(chunk)
        if archive or coverage['complete']:
            report['sha256'] = digest.hexdigest()
        report['hash_scope'] = 'archive bytes' if archive else 'sorted path, size and file bytes'

        def read(name, cap=MAX_MEMBER):
            if name not in entries:
                raise ValueError('referenced entry missing')
            entry = entries[name]
            size = entry.file_size if archive else entry.stat().st_size
            if size > cap or state['bytes_read'] + size > MAX_READ:
                limited('member or cumulative read limit reached')
                raise ValueError('entry exceeds read budget')
            # Reserve attempted expansion even if decompression or CRC checking
            # fails. Repeated corrupt entries must not bypass the total budget.
            request = min(size + 1, cap + 1, MAX_READ - state['bytes_read'])
            coverage['bytes_read'] += request
            state['bytes_read'] += request
            if archive:
                with archive.open(entry) as stream:
                    data = stream.read(request)
            else:
                with entry.open('rb') as stream:
                    data = stream.read(request)
            coverage['bytes_read'] += len(data) - request
            state['bytes_read'] += len(data) - request
            if len(data) > cap or state['bytes_read'] > MAX_READ:
                limited('member or cumulative read limit reached')
                raise ValueError('entry exceeds read budget')
            return data

        def read_json(name):
            raw = read(name, MAX_JSON)
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                if name != 'fabric.mod.json' or not exc.msg.startswith('Invalid control character'):
                    raise
                value = json.loads(raw, strict=False)
                finding('info', name,
                        {'strict_error': str(exc), 'line': exc.lineno,
                         'column': exc.colno, 'position': exc.pos,
                         'original_bytes_sha256': hashlib.sha256(raw).hexdigest(),
                         'parser': 'json.loads(strict=False)'},
                        'Fabric metadata contains literal control characters in JSON strings; '
                        'parsed using the loader-compatible control-character fallback.',
                        'Retain the original bytes; review metadata formatting if editing it.',
                        code='metadata-control-character-fallback')
            if not isinstance(value, dict):
                raise ValueError('expected JSON object')
            return value

        if 'fabric.mod.json' in entries:
            try:
                meta = read_json('fabric.mod.json')
                report['fabric'] = {key: meta.get(key) for key in
                                    ('id', 'name', 'version', 'environment', 'entrypoints', 'license', 'contact')}
                for key in ('id', 'name', 'version'):
                    report[key] = meta.get(key)
                report['fabric']['jars'] = meta.get('jars', [])
                for declaration in meta.get('jars', []):
                    nested_name = declaration.get('file') if isinstance(declaration, dict) else None
                    if not isinstance(nested_name, str) or not _safe_name(nested_name):
                        limited('invalid nested jar declaration')
                        coverage['nested_jars_inspected'] = False
                        continue
                    declared_nested.add(nested_name)
                    if nested_name not in entries:
                        limited('declared nested jar missing')
                        report['nested_jars'].append({'source_entry': nested_name,
                                                     'declared': True, 'present': False, 'inspected': False,
                                                     'archive_chain': chain + [nested_name],
                                                     'sha256': None, 'cached': False, 'report': None})
                        coverage['nested_jars_inspected'] = False
                report['fabric']['dependencies'] = {key: meta.get(key, {}) for key in
                                                     ('depends', 'recommends', 'suggests', 'breaks', 'conflicts')}
                for dependency, constraint in sorted(meta.get('depends', {}).items()):
                    finding('info', 'fabric.mod.json', {'dependency': dependency, 'constraint': constraint},
                            'Java/Fabric dependency needs an explicit native equivalent or redesign.',
                            'Verify a replacement API and its supported version.', 'dependency-replacement')
                for config in meta.get('mixins', []):
                    name = config.get('config') if isinstance(config, dict) else config
                    if not isinstance(name, str) or not _safe_name(name):
                        limited('invalid mixin config reference')
                        continue
                    try:
                        value = read_json(name)
                        package = value.get('package', '')
                        groups = {key: value.get(key, []) for key in ('mixins', 'client', 'server')}
                        report['mixins'].append({'source_entry': name, 'package': package,
                                                 'environment': config.get('environment') if isinstance(config, dict) else None,
                                                 'classes': groups, 'plugin': value.get('plugin'),
                                                 'refmap': value.get('refmap')})
                    except READ_ERRORS as exc:
                        limited('mixin config could not be read')
                        finding('warning', name, str(exc), 'Mixin coverage is incomplete.', 'Inspect the referenced config manually.')
            except READ_ERRORS + (TypeError, AttributeError, RecursionError) as exc:
                limited('Fabric metadata could not be parsed')
                finding('warning', 'fabric.mod.json', str(exc), 'Fabric metadata is malformed or exceeds limits.', 'Repair or inspect the metadata.')
        else:
            finding('info', '', 'fabric.mod.json absent', 'Fabric identity and entrypoints are unknown.', 'Confirm the loader and inspect other loader metadata.')

        patterns = {}
        for name in sorted(entries):
            lower = name.lower()
            suffix = PurePosixPath(lower).suffix
            if lower.startswith('assets/'):
                report['content']['assets'] += 1
            if lower.startswith('data/'):
                report['content']['data'] += 1
            if lower.endswith('.jar') or name in declared_nested:
                nested = {'source_entry': name, 'declared': name in declared_nested,
                          'present': True, 'inspected': False, 'archive_chain': chain + [name],
                          'sha256': None, 'cached': False, 'report': None}
                report['nested_jars'].append(nested)
                if name not in declared_nested:
                    coverage['nested_jars_inspected'] = False
                    limited('undeclared nested jar contents not inspected')
                elif depth >= MAX_NESTED_DEPTH:
                    coverage['nested_jars_inspected'] = False
                    limited('nested jar depth limit reached')
                else:
                    try:
                        nested_data = read(name, MAX_NESTED_MEMBER)
                        digest = hashlib.sha256(nested_data).hexdigest()
                        nested['sha256'] = digest
                        # Depth participates in reuse: evidence obtained at a
                        # shallower level must never bypass this path's cap.
                        cached = state['cache'].get(digest, {}).get(depth + 1)
                        if cached is not None:
                            child = _rechain(copy.deepcopy(cached), nested['archive_chain'])
                            nested['cached'] = True
                            state['cache_hits'] += 1
                        else:
                            state['inspected'] += 1
                            child = _analyze_mod(Path(name), state, depth + 1,
                                                 nested['archive_chain'], nested_data)
                            state['cache'].setdefault(digest, {})[depth + 1] = copy.deepcopy(child)
                        nested['report'] = child
                        nested['inspected'] = 'input could not be fully inspected' not in child['coverage']['limitations']
                        if not nested['inspected'] or not child['coverage']['nested_jars_inspected']:
                            coverage['nested_jars_inspected'] = False
                        if not child['coverage']['complete']:
                            limited('nested jar inspection incomplete')
                    except READ_ERRORS as exc:
                        coverage['nested_jars_inspected'] = False
                        limited('nested jar could not be read')
                        finding('warning', name, str(exc), 'Nested jar evidence is unavailable.',
                                'Inspect the declared nested jar manually.')
            for label, matches in (
                ('optifine-cem', '/optifine/cem/' in lower and suffix in ('.jem', '.jpm', '.png', '.properties')),
                ('optifine-cit', '/optifine/cit/' in lower and suffix in ('.properties', '.png', '.json')),
                ('etf-emf-resource-path', any('/' + part + '/' in lower for part in ('etf', 'emf', 'entity_texture_features', 'entity_model_features'))),
                ('shader-source', suffix in ('.vsh', '.fsh', '.glsl', '.gsh', '.csh', '.tesh', '.tcsh')),
                ('shader-config', lower.endswith('shaders.properties'))):
                if matches:
                    patterns[label] = patterns.get(label, 0) + 1
                    finding('info', name, label, 'Resource or settings data requires format compatibility review; it is not executable code.',
                            'Preserve the source asset and implement only the format features required.', 'review')
            if not lower.endswith('.class'):
                continue
            report['content']['classes'] += 1
            if coverage['classes_inspected'] >= MAX_CLASSES:
                limited('class inspection limit reached')
                continue
            try:
                evidence = _class_evidence(read(name))
                coverage['classes_inspected'] += 1
                refs = evidence.pop('references')
                evidence['source_entry'] = name
                evidence['relevant_references'] = []
                for ref in refs:
                    owner = ref['owner']
                    categories = []
                    if owner.startswith('net/fabricmc/fabric/api/event/') or (owner.startswith('net/fabricmc/fabric/api/') and ref['kind'] == 'field' and 'Event' in ref['descriptor']):
                        categories.append('fabric-event')
                    if (owner.startswith('net/fabricmc/fabric/api/client/keybinding/')
                            or owner in ('net/minecraft/client/KeyMapping',
                                         'net/minecraft/client/option/KeyBinding')):
                        categories.append('input-reference')
                    if (owner.startswith('net/fabricmc/fabric/api/client/rendering/v1/hud/')
                            or owner in ('net/fabricmc/fabric/api/client/rendering/v1/HudElementRegistry',
                                         'net/fabricmc/fabric/api/client/rendering/v1/HudRenderCallback')):
                        categories.append('hud-reference')
                    tick_owner = 'net/fabricmc/fabric/api/client/event/lifecycle/v1/ClientTickEvents'
                    if owner == tick_owner or owner.startswith(tick_owner + '$'):
                        categories.append('tick-callback-reference')
                    if '/registry/' in owner or owner.endswith('/Registry'):
                        categories.append('registry-reference')
                    if '/networking/' in owner or owner.startswith('io/netty/'):
                        categories.append('networking-reference')
                    if owner.startswith(('org/lwjgl/', 'com/mojang/blaze3d/')):
                        categories.append('graphics-native-reference')
                    if owner.startswith(('net/irisshaders/', 'net/coderbot/iris/')):
                        categories.append('shader-integration-reference')
                    if categories:
                        if len(evidence['relevant_references']) < 100:
                            evidence['relevant_references'].append({**ref, 'categories': categories})
                        else:
                            limited('per-class reference evidence limit reached')
                        finding('warning', name, {**ref, 'categories': categories},
                                'Constant-pool symbolic reference; execution and semantics have not been established.',
                                'Inspect the Java implementation and design an explicit native API mapping.', 'native-port-required')
                if evidence['mixin_annotations']:
                    finding('warning', name, evidence['mixin_annotations'],
                            'Mixin targets and injections depend on Java game internals.',
                            'Review each annotation target and redesign the behavior in the native engine.', 'native-port-required')
                report['classes'].append(evidence)
            except READ_ERRORS + (IndexError, RecursionError) as exc:
                limited('class evidence could not be parsed')
                finding('warning', name, str(exc), 'Class evidence is unavailable; no translation was attempted.', 'Inspect the class with a trusted Java analysis tool.')
        report['content']['patterns'] = dict(sorted(patterns.items()))
        if report['content']['assets'] or report['content']['data']:
            report['mapping'].append({'status': 'assets-preservable', 'reason': 'Source assets/data can be retained as migration inputs; runtime format compatibility remains unverified.'})
        if report['content']['classes']:
            report['mapping'].append({'status': 'native-port-required', 'reason': 'Java classes require manual semantic reimplementation; no class translation or native hook generation is provided.'})
        if report['fabric'] and report['fabric'].get('dependencies', {}).get('depends'):
            report['mapping'].append({'status': 'dependency-replacement', 'reason': 'Required Fabric dependencies need explicit replacement decisions.'})
        report['mapping'].append({'status': 'review', 'reason': 'Metadata, configuration and settings are data; all runtime behavior and unsupported formats require manual review.'})
    except READ_ERRORS as exc:
        limited('input could not be fully inspected')
        finding('error', '', str(exc), 'Input inspection failed or exceeded limits.', 'Supply a readable, bounded jar or directory.')
    finally:
        if archive:
            archive.close()
    report['porting_tasks'] = [
        {'status': row['mapping_status'], 'source_entry': row['source_entry'],
         'reason': row['reason'], 'next_action': row['next_action']}
        for row in report['findings'] if row['mapping_status'] != 'review'
    ]
    coverage['limitations'].sort()
    report['nested_jars'].sort(key=lambda row: row['source_entry'])
    return report
