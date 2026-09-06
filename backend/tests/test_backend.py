import io
import json
import struct
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker
from app.core.db import Base, engine
from app.core import schema
from app.models.entities import Job, Media, StorageLocation
from app.services import storage, iso_inspector as iso
from app.workers import runner


def fixture(path, architecture='x86_64'):
    data = bytearray(32 * 2048)
    def record(name, sector=0, directory=False):
        name = name.encode('ascii') if isinstance(name, str) else name
        result = bytearray(33+len(name)+(len(name)%2 == 0))
        result[0]=len(result)
        result[2:6]=struct.pack('<I',sector)
        result[10:14]=struct.pack('<I',2048 if directory else 0)
        result[25]=2 if directory else 0
        result[32]=len(name)
        result[33:33+len(name)]=name
        return result
    def directory(sector, entries):
        entries=b''.join(entries)
        data[sector*2048:sector*2048+len(entries)]=entries
    data[16*2048]=1
    data[16*2048+1:16*2048+6]=b'CD001'
    data[16*2048+156:16*2048+190]=record(b'\x00',20,True)
    data[17*2048]=255
    data[17*2048+1:17*2048+6]=b'CD001'
    directory(20,[record('CASPER',21,True),record('EFI',22,True)])
    directory(21,[record('VMLINUZ.;1'),record('INITRD.;1')])
    directory(22,[record('BOOT',23,True)])
    directory(23,[record('BOOTAA64.EFI;1' if architecture=='aarch64' else 'BOOTX64.EFI;1')])
    path.write_bytes(data)


class InspectorTests(unittest.TestCase):
    def test_casper_trailing_dots_and_architecture(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.iso'
            for arch in ['x86_64','aarch64']:
                fixture(path,arch)
                result=iso.inspect(path)
                self.assertEqual(result['detected']['architecture'],arch)
                self.assertEqual(result['recommended_adapter'],'linux-kernel-initrd')
    def test_invalid_media_and_directory_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'invalid.iso';path.write_bytes(bytes(64*2048))
            with self.assertRaises(iso.IsoError): iso.inspect(path)
        with self.assertRaises(iso.IsoError): iso.read_dir(io.BytesIO(),0,17*1024*1024)


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema_name='test_'+uuid.uuid4().hex
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA {cls.schema_name}'))
        cls.engine=create_engine(engine.url,connect_args={'options':f'-csearch_path={cls.schema_name}'})
        cls.session=sessionmaker(bind=cls.engine,expire_on_commit=False)
        with patch.object(schema,'engine',cls.engine): schema.initialize_schema()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        with engine.begin() as conn: conn.execute(text(f'DROP SCHEMA {cls.schema_name} CASCADE'))

    def setUp(self):
        with self.engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables): conn.execute(table.delete())

    def test_upgrade_and_large_file_metadata(self):
        with self.engine.begin() as conn: conn.execute(text('ALTER TABLE media ALTER COLUMN size_bytes TYPE INTEGER'))
        with patch.object(schema,'engine',self.engine): schema.initialize_schema()
        with self.session() as db:
            store=StorageLocation(name='test',path='/storage');db.add(store);db.flush()
            media=Media(storage_id=store.id,relative_path='large.iso',name='large.iso',size_bytes=5*1024**3)
            db.add(media);db.commit()
            self.assertEqual(db.get(Media,media.id).size_bytes,5*1024**3)

    def test_claim_skips_locked_job(self):
        with self.session() as db:
            db.add_all([Job(kind='analyze-iso'),Job(kind='analyze-iso')]);db.commit()
        with self.session() as first, self.session() as second:
            locked=first.scalars(select(Job).order_by(Job.id).with_for_update().limit(1)).one()
            claimed=runner.claim_job(second)
            self.assertNotEqual(claimed,locked.id)
            self.assertEqual(second.get(Job,claimed).status,'running')

    def test_failed_transaction_records_error_and_worker_continues(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); fixture(root/'valid.iso')
            with self.session() as db:
                store=StorageLocation(name='source',path=folder);db.add(store);db.flush()
                job=Job(kind='analyze-iso',status='running',payload_json=json.dumps({'storage_id':store.id,'relative_path':'valid.iso'}));db.add(job);db.commit();job_id=job.id
            with patch.object(runner,'SessionLocal',self.session),patch.object(storage,'STORAGE_ROOT',root),patch.object(runner,'heartbeat'),patch.object(runner,'sha256',return_value='x'*65):
                runner.process_job(job_id)
            with self.session() as db:
                failed=db.get(Job,job_id)
                self.assertEqual(failed.status,'failed')
                self.assertIn('DataError',failed.log_text)
                follow=Job(kind='analyze-iso',payload_json=failed.payload_json);db.add(follow);db.commit()
                follow_id=runner.claim_job(db)
            with patch.object(runner,'SessionLocal',self.session),patch.object(storage,'STORAGE_ROOT',root),patch.object(runner,'heartbeat'):
                runner.process_job(follow_id)
            with self.session() as db: self.assertEqual(db.get(Job,follow_id).status,'complete')

    def test_abandoned_job_expires(self):
        with self.session() as db:
            job=Job(kind='analyze-iso',status='running',updated_at=datetime.utcnow()-timedelta(minutes=10));db.add(job);db.commit()
            runner.claim_job(db);db.expire_all()
            self.assertEqual(db.get(Job,job.id).status,'failed')


class StorageTests(unittest.TestCase):
    def test_boundary_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'library').mkdir();(root/'library'/'escape').symlink_to('/etc')
            with patch.object(storage,'STORAGE_ROOT',root):
                self.assertEqual(storage.safe_resolve(str(root/'library'),'image.iso'),root/'library'/'image.iso')
                for base,relative in [('/etc','passwd'),(str(root/'library'),'../outside'),(str(root/'library'),'escape/passwd'),(str(root/'library'),'/etc/passwd')]:
                    with self.assertRaises(ValueError): storage.safe_resolve(base,relative)

if __name__=='__main__': unittest.main()
