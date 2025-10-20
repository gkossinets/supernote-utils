import unittest
import os
import subprocess

class TestNoteToPdf(unittest.TestCase):
    """Test the note2pdf.py script"""

    def test_conversion(self):
        """Test that a .note file is converted to a .pdf file"""
        input_file = "test/test.note"
        output_file = "test/test.pdf"

        # Ensure the output file doesn't exist before the test
        if os.path.exists(output_file):
            os.remove(output_file)

        # Run the script
        subprocess.run(["python3", "note2pdf.py", input_file, output_file], check=True)

        # Check that the output file was created
        self.assertTrue(os.path.exists(output_file))

        # Clean up the output file
        os.remove(output_file)

if __name__ == '__main__':
    unittest.main()
