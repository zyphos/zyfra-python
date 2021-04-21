import sys
import imp
from decimal import Decimal

f, path, descr = imp.find_module('csv', sys.path[1:])
python_csv = imp.load_module('csv', f, path, descr)

class CSVfile(object):
    def __init__(self, file, delimiter=',', quotechar='"', auto_detect=False, debug=False):
        self.debug = debug
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.file = file
        self.auto_detect = auto_detect
        #if not self.debug:
        #    self.f = open(os.path.join(script_path, 'export', filename), 'w')
            
    def render_field(self, data):
        try:
            if isinstance(data, str):
                return '%s%s%s' % (self.quotechar, data.replace(self.quotechar,self.quotechar+self.quotechar), self.quotechar)
            elif isinstance(data, list):
                if data:
                    return '[%s]' % ','.join(data)
                else:
                    return ''
            elif data is None:
                return ''
            elif isinstance(data, float):
                return self.render_field(str(float(data)).replace('.',','))
            elif isinstance(data, Decimal):
                return self.render_field(str(data).replace('.',','))
            return unicode(str(data))
        except:
            print(repr(data))
            raise
    
    def write(self, *args):
        rendered_args = [self.render_field(v) for v in args]
        try:
            rendered_data = self.delimiter.join(rendered_args)
        except:
            print(rendered_args)
            raise
        if self.debug:
            print(rendered_data)
        else:
            try:
                self.file.write((rendered_data + '\n').encode('utf8'))
            except:
                print(rendered_data)
                print(repr(rendered_data))
                raise
    
    def read_file(self, nb_max_rows=0):
        rows = []
        if self.auto_detect:
            self.file.seek(0)
            dialect = python_csv.Sniffer().sniff(self.file.read(1024))
            self.file.seek(0)
            reader = python_csv.reader(self.file, dialect)
        else:
            reader = python_csv.reader(self.file, delimiter=self.delimiter, quotechar=self.quotechar)
        i = 0
        for row in reader:
            i += 1
            if nb_max_rows and i > nb_max_rows:
                break
            rows.append(row)
        return rows
   
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        if not self.debug:
            self.f.close()
