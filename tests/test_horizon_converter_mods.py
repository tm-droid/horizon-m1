"""Small generated JVM class fixtures keep tests independent of a Java install."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile


SPEC = importlib.util.spec_from_file_location(
    'horizon_converter_mods', Path(__file__).resolve().parents[1] / 'tools/horizon_converter_mods.py')
mods = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mods)


def u2(value):
    return struct.pack('>H', value)


def u4(value):
    return struct.pack('>I', value)


def class_fixture():
    """Valid Java 8 class with a constructor, annotation, and symbolic API refs.

    API references are intentionally unused in Code: the report must not claim
    that a constant-pool member reference proves execution.
    """
    pool = []

    def add(tag, payload):
        pool.append(bytes([tag]) + payload)
        return len(pool)

    def utf(value):
        data = value.encode('utf-8')
        return add(1, u2(len(data)) + data)

    def cls(value):
        return add(7, u2(utf(value)))

    def member(tag, owner, name, descriptor):
        owner_idx = cls(owner)
        name_idx, descriptor_idx = utf(name), utf(descriptor)
        nt = add(12, u2(name_idx) + u2(descriptor_idx))
        return add(tag, u2(owner_idx) + u2(nt))

    this, parent = cls('example/Test'), cls('java/lang/Object')
    init_name, init_desc, code_name = utf('<init>'), utf('()V'), utf('Code')
    super_init = member(10, 'java/lang/Object', '<init>', '()V')
    member(9, 'net/fabricmc/fabric/api/client/event/lifecycle/v1/ClientTickEvents',
           'END_CLIENT_TICK', 'Lnet/fabricmc/fabric/api/event/Event;')
    member(10, 'net/fabricmc/fabric/api/client/keybinding/v1/KeyBindingHelper',
           'registerKeyBinding', '(Lnet/minecraft/client/KeyMapping;)Lnet/minecraft/client/KeyMapping;')
    member(10, 'net/minecraft/client/KeyMapping', 'consumeClick', '()Z')
    member(10, 'net/fabricmc/fabric/api/client/rendering/v1/hud/HudElementRegistry',
           'addLast', '(Ljava/lang/Object;)V')
    member(9, 'net/fabricmc/fabric/api/client/rendering/v1/HudRenderCallback',
           'EVENT', 'Lnet/fabricmc/fabric/api/event/Event;')
    member(11, 'net/fabricmc/fabric/api/client/event/lifecycle/v1/ClientTickEvents$EndTick',
           'onEndTick', '(Ljava/lang/Object;)V')
    member(10, 'org/lwjgl/opengl/GL11', 'glClear', '(I)V')
    member(10, 'net/minecraft/registry/Registry', 'register', '(Ljava/lang/Object;)V')
    member(10, 'net/fabricmc/fabric/api/networking/v1/ClientPlayNetworking', 'send', '()V')
    annotations_name = utf('RuntimeInvisibleAnnotations')
    mixin_desc, value_name, target = utf('Lorg/spongepowered/asm/mixin/Mixin;'), utf('value'), utf('Lnet/minecraft/Client;')
    mixin_annotation = u2(1) + u2(mixin_desc) + u2(1) + u2(value_name) + b'[' + u2(1) + b'c' + u2(target)
    inject_desc, method_name, tick_name = utf('Lorg/spongepowered/asm/mixin/injection/Inject;'), utf('method'), utf('tick')
    at_name, at_desc, head = utf('at'), utf('Lorg/spongepowered/asm/mixin/injection/At;'), utf('HEAD')
    inject_annotation = (u2(1) + u2(inject_desc) + u2(2) + u2(method_name)
                         + b'[' + u2(1) + b's' + u2(tick_name)
                         + u2(at_name) + b'@' + u2(at_desc) + u2(1)
                         + u2(value_name) + b's' + u2(head))
    tick = utf('onTick')

    def attr(name, body):
        return u2(name) + u4(len(body)) + body

    def code(instructions, stack, locals_count):
        return attr(code_name, u2(stack) + u2(locals_count) + u4(len(instructions))
                    + instructions + u2(0) + u2(0))

    constructor = (u2(1) + u2(init_name) + u2(init_desc) + u2(1)
                   + code(b'\x2a\xb7' + u2(super_init) + b'\xb1', 1, 1))
    tick_method = (u2(9) + u2(tick) + u2(init_desc) + u2(2)
                   + code(b'\xb1', 0, 0) + attr(annotations_name, inject_annotation))
    return (b'\xca\xfe\xba\xbe' + u2(0) + u2(52) + u2(len(pool) + 1)
            + b''.join(pool) + u2(0x21) + u2(this) + u2(parent)
            + u2(0) + u2(0) + u2(2) + constructor + tick_method
            + u2(1) + attr(annotations_name, mixin_annotation))


class AnalyzeModTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def jar(self, entries):
        path = self.root / 'example.jar'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, value in entries.items():
                archive.writestr(name, value)
        return path

    def test_actual_class_references_annotations_and_determinism(self):
        metadata = {'id': 'example', 'name': 'Example', 'version': '1',
                    'environment': 'client', 'license': ['MIT'],
                    'contact': {'sources': 'https://example.invalid/source',
                                'issues': 'https://example.invalid/issues',
                                'homepage': 'https://example.invalid/'},
                    'entrypoints': {'client': ['example.Test']},
                    'depends': {'fabric-api': '*'}, 'mixins': ['example.mixins.json'],
                    'jars': [{'file': 'nested/library.jar'}]}
        path = self.jar({'fabric.mod.json': json.dumps(metadata),
                         'example.mixins.json': json.dumps({'package': 'example', 'client': ['Test']}),
                         'example/Test.class': class_fixture(),
                         'assets/example/optifine/cem/cow.jem': '{}',
                         'assets/example/shaders/a.fsh': 'void main() {}',
                         'data/example/test.json': '{}', 'nested/library.jar': b'not executed'})
        original = path.read_bytes()
        report = mods.analyze_mod(path)
        self.assertEqual(report, mods.analyze_mod(path))
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(report['id'], 'example')
        self.assertEqual(report['fabric']['license'], ['MIT'])
        self.assertEqual(report['fabric']['contact'], metadata['contact'])
        self.assertEqual(report['content']['assets'], 2)
        self.assertEqual(report['content']['data'], 1)
        self.assertEqual(report['coverage']['classes_inspected'], 1)
        self.assertFalse(report['coverage']['nested_jars_inspected'])
        self.assertFalse(report['coverage']['complete'])
        evidence = report['classes'][0]
        categories = {category for ref in evidence['relevant_references'] for category in ref['categories']}
        self.assertEqual(categories, {'fabric-event', 'graphics-native-reference',
                                     'registry-reference', 'networking-reference',
                                     'input-reference', 'hud-reference', 'tick-callback-reference'})
        by_member = {(ref['owner'], ref['name']): set(ref['categories'])
                     for ref in evidence['relevant_references']}
        self.assertIn('input-reference', by_member[(
            'net/fabricmc/fabric/api/client/keybinding/v1/KeyBindingHelper', 'registerKeyBinding')])
        self.assertIn('hud-reference', by_member[(
            'net/fabricmc/fabric/api/client/rendering/v1/hud/HudElementRegistry', 'addLast')])
        self.assertEqual(by_member[(
            'net/fabricmc/fabric/api/client/event/lifecycle/v1/ClientTickEvents', 'END_CLIENT_TICK')],
            {'fabric-event', 'tick-callback-reference'})
        injection = evidence['mixin_annotations'][0]
        self.assertEqual(injection['values']['method'], ['tick'])
        self.assertEqual(injection['values']['at']['values']['value'], 'HEAD')
        target = evidence['mixin_annotations'][1]['values']['value'][0]['class']
        self.assertEqual(target, 'Lnet/minecraft/Client;')
        self.assertEqual(report['mixins'][0]['classes']['client'], ['Test'])
        self.assertIn('native-port-required', {row['status'] for row in report['mapping']})
        self.assertTrue(any('not been established' in f['reason'] for f in report['findings']))
        json.dumps(report)

    def test_unsafe_paths_and_zip_symlinks_are_never_read(self):
        path = self.jar({'../escape': b'secret', '/absolute': b'secret',
                         'C:\\escape': b'secret', 'assets/example/a.png': b'ok'})
        with zipfile.ZipFile(path, 'a') as archive:
            symlink = zipfile.ZipInfo('fabric.mod.json')
            symlink.create_system = 3
            symlink.external_attr = 0o120777 << 16
            archive.writestr(symlink, '/etc/passwd')
        result = mods.analyze_mod(path)
        self.assertIsNone(result['fabric'])
        self.assertFalse(result['coverage']['complete'])
        self.assertEqual(result['coverage']['bytes_read'], 0)
        self.assertFalse((self.root.parent / 'escape').exists())

    def test_directory_hash_and_symlink_boundary(self):
        directory = self.root / 'mod'
        directory.mkdir()
        (directory / 'fabric.mod.json').write_text('{"id":"dir","version":"1"}')
        first = mods.analyze_mod(directory)
        self.assertIsNotNone(first['sha256'])
        self.assertEqual(first, mods.analyze_mod(directory))
        (directory / 'config.json').write_text('{"setting":"data"}')
        self.assertNotEqual(first['sha256'], mods.analyze_mod(directory)['sha256'])
        (directory / 'external').symlink_to(self.root / 'outside')
        result = mods.analyze_mod(directory)
        self.assertIsNone(result['sha256'])
        self.assertIn('directory symlinks skipped', result['coverage']['limitations'])

    def test_bad_metadata_classes_and_archive_are_reported(self):
        path = self.jar({'fabric.mod.json': '{invalid', 'Bad.class': b'\xca\xfe\xba\xbe\x00'})
        result = mods.analyze_mod(path)
        self.assertFalse(result['coverage']['complete'])
        self.assertEqual(len([f for f in result['findings'] if f['severity'] == 'warning']), 2)
        path.write_bytes(b'not a zip')
        self.assertEqual(mods.analyze_mod(path)['findings'][0]['severity'], 'error')

    def test_compressed_metadata_bomb_is_not_expanded(self):
        path = self.root / 'bomb.jar'
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('fabric.mod.json', b' ' * (mods.MAX_JSON + 1))
        result = mods.analyze_mod(path)
        self.assertEqual(result['coverage']['bytes_read'], 0)
        self.assertIn('member or cumulative read limit reached', result['coverage']['limitations'])

    def test_corrupt_deflate_is_reported_and_read_budget_reserved(self):
        path = self.root / 'corrupt.jar'
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('fabric.mod.json', '{"id":"example"}')
        raw = bytearray(path.read_bytes())
        name_length, extra_length = struct.unpack_from('<HH', raw, 26)
        offset = 30 + name_length + extra_length
        raw[offset] = 0x07  # Deflate block type 3 is reserved/invalid.
        path.write_bytes(raw)
        result = mods.analyze_mod(path)
        self.assertFalse(result['coverage']['complete'])
        self.assertGreater(result['coverage']['bytes_read'], 0)
        self.assertTrue(result['findings'])

    def test_cumulative_read_and_class_limits_are_explicit(self):
        path = self.jar({'First.class': class_fixture(), 'Second.class': class_fixture()})
        with patch.object(mods, 'MAX_CLASSES', 1):
            result = mods.analyze_mod(path)
        self.assertEqual(result['content']['classes'], 2)
        self.assertEqual(result['coverage']['classes_inspected'], 1)
        self.assertIn('class inspection limit reached', result['coverage']['limitations'])
        with patch.object(mods, 'MAX_READ', 8):
            result = mods.analyze_mod(path)
        self.assertEqual(result['coverage']['bytes_read'], 0)
        self.assertFalse(result['coverage']['complete'])

    def test_malformed_annotation_and_constant_pool_are_bounded(self):
        for data in (class_fixture()[:-3], b'\xca\xfe\xba\xbe' + u2(0) + u2(52) + u2(2) + b'\xff'):
            with self.assertRaises(ValueError):
                mods._class_evidence(data)

    def test_missing_mixin_and_nested_jar_declarations_remain_visible(self):
        path = self.jar({'fabric.mod.json': json.dumps({'id': 'x', 'mixins': ['absent.json'],
                         'jars': [{'file': 'missing.jar'}]})})
        result = mods.analyze_mod(path)
        self.assertEqual(result['fabric']['jars'], [{'file': 'missing.jar'}])
        self.assertEqual(result['nested_jars'][0]['present'], False)
        self.assertTrue(any(f['source_entry'] == 'absent.json' for f in result['findings']))

    def nested_bytes(self, entries):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            for name, value in entries.items():
                archive.writestr(name, value)
        return output.getvalue()

    def test_loader_control_character_metadata_fallback_preserves_original_bytes(self):
        metadata = b'{"id":"emf","version":"3.3.12","description":"Models\nTextures\tDetails\rMore"}'
        path = self.jar({'fabric.mod.json': metadata})
        original = path.read_bytes()
        result = mods.analyze_mod(path)
        self.assertEqual(result['id'], 'emf')
        self.assertTrue(result['coverage']['complete'])
        fallback = [row for row in result['findings']
                    if row['code'] == 'metadata-control-character-fallback']
        self.assertEqual(len(fallback), 1)
        evidence = fallback[0]['evidence']
        self.assertEqual(evidence['original_bytes_sha256'], hashlib.sha256(metadata).hexdigest())
        self.assertIn('Invalid control character', evidence['strict_error'])
        self.assertEqual(evidence['parser'], 'json.loads(strict=False)')
        self.assertEqual(result['sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(path.read_bytes(), original)

    def test_control_character_fallback_does_not_accept_other_json_syntax(self):
        for metadata in (b'{"id":"bad",}', b"{'id':'bad'}",
                         b'{"id":"bad","description":"a\nb",}'):
            result = mods.analyze_mod(self.jar({'fabric.mod.json': metadata}))
            self.assertFalse(result['coverage']['complete'])
            self.assertIsNone(result['fabric'])
            self.assertFalse(any(row['code'] == 'metadata-control-character-fallback'
                                 for row in result['findings']))

    def test_nested_hash_cache_retains_each_archive_chain_and_categories(self):
        leaf = self.nested_bytes({'fabric.mod.json': '{"id":"leaf","name":"Leaf"}',
                                  'Example.class': class_fixture()})
        metadata = {'id': 'root', 'jars': [{'file': 'a.jar'}, {'file': 'b.jar'}]}
        path = self.jar({'fabric.mod.json': json.dumps(metadata), 'a.jar': leaf, 'b.jar': leaf})
        result = mods.analyze_mod(path)
        first, second = result['nested_jars']
        self.assertTrue(first['inspected'])
        self.assertFalse(first['cached'])
        self.assertTrue(second['cached'])
        self.assertEqual(first['sha256'], hashlib.sha256(leaf).hexdigest())
        self.assertEqual(first['sha256'], second['sha256'])
        self.assertEqual(first['report']['archive_chain'], [str(path), 'a.jar'])
        self.assertEqual(second['report']['archive_chain'], [str(path), 'b.jar'])
        self.assertEqual(second['report']['name'], 'Leaf')
        self.assertEqual(second['report']['path'], str(path) + '!/b.jar')
        self.assertTrue(second['report']['classes'][0]['relevant_references'])
        self.assertEqual(result['coverage']['nested_stats'],
                         {'archives_inspected': 1, 'cache_hits': 1, 'unique_hashes': 1})
        self.assertTrue(result['coverage']['complete'])
        self.assertTrue(result['coverage']['nested_jars_inspected'])

    def test_recursive_cache_rebases_descendant_chains(self):
        leaf = self.nested_bytes({'fabric.mod.json': '{"id":"leaf"}'})
        branch = self.nested_bytes({'fabric.mod.json': json.dumps(
            {'id': 'branch', 'jars': [{'file': 'leaf.jar'}]}), 'leaf.jar': leaf})
        path = self.jar({'fabric.mod.json': json.dumps({'jars': [{'file': 'a.jar'}, {'file': 'b.jar'}]}),
                         'a.jar': branch, 'b.jar': branch})
        result = mods.analyze_mod(path)
        cached_leaf = result['nested_jars'][1]['report']['nested_jars'][0]
        self.assertEqual(cached_leaf['archive_chain'], [str(path), 'b.jar', 'leaf.jar'])
        self.assertEqual(cached_leaf['report']['archive_chain'], cached_leaf['archive_chain'])

    def test_nested_unsafe_entry_and_missing_declared_member_are_incomplete(self):
        child = self.nested_bytes({'../unsafe.class': class_fixture(),
                                   'fabric.mod.json': json.dumps({'jars': [{'file': 'missing.jar'}]})})
        path = self.jar({'fabric.mod.json': json.dumps({'jars': [{'file': 'child.jar'}]}),
                         'child.jar': child})
        result = mods.analyze_mod(path)
        node = result['nested_jars'][0]['report']
        self.assertFalse(result['coverage']['complete'])
        self.assertTrue(result['coverage']['incomplete'])
        self.assertFalse(result['coverage']['nested_jars_inspected'])
        self.assertIn('unsafe archive entries skipped', node['coverage']['limitations'])
        self.assertEqual(node['coverage']['bytes_read'], len(json.dumps({'jars': [{'file': 'missing.jar'}]})))
        self.assertFalse(node['nested_jars'][0]['present'])
        self.assertIsNone(node['nested_jars'][0]['report'])

    def test_nested_depth_and_shared_read_budget_caps(self):
        leaf = self.nested_bytes({'fabric.mod.json': '{"id":"leaf"}'})
        branch_metadata = json.dumps({'jars': [{'file': 'leaf.jar'}]})
        branch = self.nested_bytes({'fabric.mod.json': branch_metadata, 'leaf.jar': leaf})
        root_metadata = json.dumps({'jars': [{'file': 'branch.jar'}]})
        path = self.jar({'fabric.mod.json': root_metadata, 'branch.jar': branch})
        with patch.object(mods, 'MAX_NESTED_DEPTH', 1):
            result = mods.analyze_mod(path)
        node = result['nested_jars'][0]['report']
        self.assertIn('nested jar depth limit reached', node['coverage']['limitations'])
        self.assertFalse(node['nested_jars'][0]['inspected'])
        self.assertTrue(result['coverage']['incomplete'])
        # The outer jar bytes fit; expansion within the child must still debit
        # the same budget and stop before its metadata is read.
        budget = len(root_metadata) + len(branch)
        with patch.object(mods, 'MAX_READ', budget):
            result = mods.analyze_mod(path)
        self.assertEqual(result['coverage']['total_bytes_read'], budget)
        self.assertTrue(result['coverage']['incomplete'])
        self.assertIn('member or cumulative read limit reached',
                      result['nested_jars'][0]['report']['coverage']['limitations'])

    def test_nested_member_cap_and_case_distinct_classes(self):
        child = self.nested_bytes({'Example.class': class_fixture(), 'example.class': class_fixture()})
        metadata = json.dumps({'jars': [{'file': 'child.jar'}]})
        path = self.jar({'fabric.mod.json': metadata, 'child.jar': child})
        result = mods.analyze_mod(path)
        self.assertEqual(result['nested_jars'][0]['report']['coverage']['classes_inspected'], 2)
        self.assertTrue(result['coverage']['complete'])
        with patch.object(mods, 'MAX_NESTED_MEMBER', len(child) - 1):
            result = mods.analyze_mod(path)
        self.assertFalse(result['nested_jars'][0]['inspected'])
        self.assertEqual(result['coverage']['total_bytes_read'], len(metadata))
        self.assertTrue(result['coverage']['incomplete'])

    def test_wrong_metadata_collection_types_do_not_crash(self):
        for key in ('jars', 'depends', 'mixins'):
            path = self.jar({'fabric.mod.json': json.dumps({'id': 'bad', key: None})})
            result = mods.analyze_mod(path)
            self.assertFalse(result['coverage']['complete'])
            self.assertTrue(result['findings'])


if __name__ == '__main__':
    unittest.main()
