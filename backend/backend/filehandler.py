import os
import shutil


class FileHandle:
    def copytree(self, src: str, dst: str, symlinks=False, ignore=None):
        """Source: https://stackoverflow.com/questions/1868714/how-do-i-copy-an-entire-directory-of-files-into-an-existing-directory-using-pyth
        Copies a folder/file structure from src to dst
        :param src: Source path of folder/file
        :type src: string
        :param dst: Destination path for folder/file
        :type dst: string
        """
        for item in os.listdir(src):
            source = os.path.join(src, item)
            destination = os.path.join(dst, item)
            if os.path.isdir(source):
                shutil.copytree(source, destination, symlinks, ignore)
            else:
                shutil.copy2(source, destination)

    def replaceStringInFile(self, file: str, old_string: str, new_string: str):
        """Source: https://stackoverflow.com/questions/4128144/replace-string-within-file-contents
        Replaces old_string with new_string in file
        :param file: Source path of file
        :type file: string
        :param old_string: Old string to be replaced
        :type old_string: string
        :param new_string: New string
        :type new_string: string
        """
        tmp = file + "tmp"
        os.rename(file, tmp)
        with open(tmp, "rt") as fin:
            with open(file, "w", newline="\n") as fout:
                for line in fin:
                    fout.write(line.replace(old_string, new_string))
