import pytest
import os
import tempfile
import shutil
from library4agents.models import Expertise, Observation
from library4agents.storage import JsonStorage, MarkdownStorage, VCSMarkdownStorage

@pytest.fixture
def temp_json_storage():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        file_path = f.name
    storage = JsonStorage(file_path)
    yield storage
    os.unlink(file_path)

@pytest.fixture
def temp_md_storage():
    dir_path = tempfile.mkdtemp()
    storage = MarkdownStorage(dir_path)
    yield storage
    shutil.rmtree(dir_path)

def test_json_storage_save_and_get_all(temp_json_storage):
    exp1 = Expertise(territory="A", guide="B", treasures=[Observation("C")])
    temp_json_storage.save(exp1)
    
    all_exp = temp_json_storage.get_all()
    assert len(all_exp) == 1
    assert all_exp[0].territory == "A"
    assert all_exp[0].treasures[0].description == "C"

def test_markdown_storage_save_and_get_all(temp_md_storage):
    exp1 = Expertise(territory="Web", guide="Use Python", treasures=[Observation("Fast", "C-based")])
    temp_md_storage.save(exp1)
    
    all_exp = temp_md_storage.get_all()
    assert len(all_exp) == 1
    assert all_exp[0].territory == "Web"
    assert all_exp[0].guide == "Use Python"
    assert all_exp[0].treasures[0].description == "Fast"
    assert all_exp[0].treasures[0].rationale == "C-based"
    
    # Update existing
    exp1.guide = "Use JS"
    temp_md_storage.save(exp1)
    
    all_exp = temp_md_storage.get_all()
    assert len(all_exp) == 1
    assert all_exp[0].guide == "Use JS"

def test_storage_multiple_items(temp_md_storage):
    exp1 = Expertise(territory="A", guide="B")
    exp2 = Expertise(territory="X", guide="Y")
    
    temp_md_storage.save(exp1)
    temp_md_storage.save(exp2)
    
    all_exp = temp_md_storage.get_all()
    assert len(all_exp) == 2

def test_vcs_storage_path_traversal_rejection():
    temp_dir = tempfile.mkdtemp()
    try:
        storage = VCSMarkdownStorage(temp_dir)
        
        # Path traversal attempts must raise ValueError
        with pytest.raises(ValueError, match="Invalid or unsafe branch name"):
            storage.create_branch("../escaped")

        with pytest.raises(ValueError, match="Invalid or unsafe branch name"):
            storage.create_branch("foo/../../bar")

        with pytest.raises(ValueError, match="Invalid or unsafe branch name"):
            storage.create_branch("branch with spaces")

        with pytest.raises(ValueError, match="Invalid or unsafe branch name"):
            storage.create_branch("bad;rm -rf")

        with pytest.raises(ValueError, match="Invalid or unsafe branch name"):
            storage.create_branch("")

        # Valid branch names must be accepted
        storage.create_branch("hypothesis/safe-branch")
        assert "hypothesis/safe-branch" in storage.list_branches()
        
        storage.create_branch("feature_123.v2")
        assert "feature_123.v2" in storage.list_branches()
    finally:
        shutil.rmtree(temp_dir)

