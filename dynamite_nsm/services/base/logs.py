import os
import gzip
import linecache


class LogFileSize:

    def __init__(self, file_line_count, loaded_entries):
        self.file_line_count = file_line_count
        self.loaded_entries = loaded_entries


class LogFile:

    def __init__(self, log_path, log_sample_size=500, gzip_decode=False):
        """
        :param log_path: The path to a log file
        :param log_sample_size: The number of most recent entries to include
        :param gzip_decode: If True, we'll decode the log before reading it in
        """

        self.log_path = log_path
        self.exists = False
        self.current_line = 0
        if gzip_decode and not log_path.endswith('.decoded'):
            decoded_log_path = log_path + '.decoded'
            if not os.path.exists(decoded_log_path):
                with open(decoded_log_path, 'w') as out:
                    with gzip.open(log_path, 'rb') as f:
                        line = f.readline().decode('utf-8', errors='ignore')
                        while line:
                            out.write(line)
                            try:
                                line = f.readline().decode('utf-8', errors='ignore')
                            except gzip.BadGzipFile:
                                pass

            self.log_path = decoded_log_path
        linecache.updatecache(self.log_path)
        self.last_line_num = self.find_latest_line_offset()
        if self.last_line_num < log_sample_size:
            self.entries = [entry for entry in self.iter_cache(start=1)]
        else:
            self.entries = [entry for entry in self.iter_cache(start=self.last_line_num - log_sample_size + 1)]

    def __len__(self):
        return self.last_line_num

    def __iter__(self):
        return self

    def __next__(self):
        self.current_line += 1
        line = linecache.getline(self.log_path, self.current_line)
        if line:
            return line
        else:
            raise StopIteration

    def iter_cache(self, start=1, step=1):
        """
        Relatively Memory efficient method of accessing very large files on disk

        :param start: The starting line
        :param step: The step between line offsets
        :return: The line at a particular offset
        """

        i = start
        while True:
            line = linecache.getline(self.log_path, i)
            if line:
                yield line
            else:
                break
            i += step

    def find_latest_line_offset(self, step=500000):
        """
        Relatively fast way of finding the latest offset; algorithm guesses
        high offset and if over divides the step by half and repeats

        :param step: The starting step between line offsets
        :return: Most recent line number
        """
        offset = 1
        while step > 0:
            for _ in self.iter_cache(start=offset, step=step):
                offset += step
            step = int(step/2)
            offset -= step
        return offset

    def size(self):
        return LogFileSize(self.find_latest_line_offset(), len(self.entries))
