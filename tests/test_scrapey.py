import unittest
from pathlib import Path
import shutil
from scrapey import sanitize_filename, create_directory, rename_files, apply_filters

class TestScrapey(unittest.TestCase):

    def test_create_directory(self):
        test_dir = Path("test_temp_dir")
        self.assertFalse(test_dir.exists())
        self.assertTrue(create_directory(test_dir))
        self.assertTrue(test_dir.is_dir())
        # Test creating an existing directory
        self.assertTrue(create_directory(test_dir))
        # Clean up
        test_dir.rmdir()

    def test_rename_files(self):
        # Create a temporary directory for testing
        test_dir = Path("test_rename_dir")
        test_dir.mkdir(exist_ok=True)

        # Create dummy files
        file1 = test_dir / "image1.jpg"
        file2 = test_dir / "image2.png"
        file3 = test_dir / "image3.gif"
        file1.touch()
        file2.touch()
        file3.touch()

        file_paths = [file1, file2, file3]
        base_query = "test_query"

        renamed_paths = rename_files(file_paths, base_query)

        self.assertEqual(len(renamed_paths), 3)
        self.assertTrue((test_dir / "test_query_0001.jpg").exists())
        self.assertTrue((test_dir / "test_query_0002.png").exists())
        self.assertTrue((test_dir / "test_query_0003.gif").exists())

        # Test collision handling
        file4 = test_dir / "test_query_0001.jpg"
        file4.touch()
        renamed_paths_collision = rename_files([file4], base_query)
        self.assertEqual(len(renamed_paths_collision), 1)
        self.assertTrue((test_dir / "test_query_0001_1.jpg").exists())

        # Clean up
        shutil.rmtree(test_dir)

    def test_apply_filters(self):
        self.assertEqual(apply_filters(size="Large", type="Photo"), "Size:Large+Type:Photo")
        self.assertEqual(apply_filters(color="monochrome"), "Color:Monochrome")
        self.assertEqual(apply_filters(color="red"), "Color:Red")
        self.assertEqual(apply_filters(unknown_filter="value"), "")
        self.assertEqual(apply_filters(size="Small", people="face", date="pastweek"), "Size:Small+People:Face+Date:Pastweek")
        self.assertEqual(apply_filters(), "")

    def test_create_directory(self):
        test_dir = Path("test_temp_dir")
        self.assertFalse(test_dir.exists())
        self.assertTrue(create_directory(test_dir))
        self.assertTrue(test_dir.is_dir())
        # Test creating an existing directory
        self.assertTrue(create_directory(test_dir))
        # Clean up
        test_dir.rmdir()

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("  My Test File.jpg "), "My_Test_File_jpg")
        self.assertEqual(sanitize_filename("File with !@#$%^&*() special chars"), "File_with_special_chars")
        self.assertEqual(sanitize_filename("Another_file-with spaces"), "Another_file-with_spaces")
        self.assertEqual(sanitize_filename("long_filename_" * 20), ("long_filename_" * 20)[:200])
        self.assertEqual(sanitize_filename("  "), "")

    # Add more tests for other functions as they are refactored/improved

if __name__ == '__main__':
    unittest.main()