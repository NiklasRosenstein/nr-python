
from io import BytesIO
from nr.fs import atomic_file, tempfile
from nr.collections.persistable import JsonPersister, FilePersister, \
  PersistableDict


def test_persistable_dict_json():
  m = PersistableDict(JsonPersister())
  m['abc'] = 42

  fp = BytesIO()
  m.save(fp)

  assert fp.getvalue().decode('utf-8') == '{"abc": 42}'

  fp.seek(0)
  n = PersistableDict(JsonPersister())
  n.load(fp)
  assert n == m


def test_file_persister():
  # Create a new temporary file for this test.
  with tempfile() as tmp:
    tmp.close()

    # Create a persister to this temporary file.
    persister = FilePersister(JsonPersister(), tmp.name)
    assert persister.exists()

    # Populate the file.
    m = PersistableDict(persister)
    m['abc'] = 42
    m.save()

    # Load the file.
    m = PersistableDict(persister)
    m.load()

    assert m['abc'] == 42
