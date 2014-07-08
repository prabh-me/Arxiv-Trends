import sqlite3
import pickle
import datetime
import os

fields = [("date", "timestamp"), ("url", "text", "primary key")
          , ("abstract", "text"), ("subject", "text")
          , ("title", "text"), ("authors", "text"),
          ]

connection_options = {'detect_types' : sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES}

def connect(sql_file, opts = None):
    if opts == None:
        opts = connection_options

    conn = sqlite3.connect(sql_file, **opts)
    conn.row_factory = sqlite3.Row
    return conn

def create_sqlite(sql_file): 
    conn = sqlite3.connect(sql_file, **connection_options)

    command = "create table articles("
    for field in fields:
        command += " ".join(field) + ","
    command = command[:-1] + ")"
    conn.execute(command)

    command = "create table words(word text, date timestamp)"
    conn.execute(command)
    
    conn.commit()

def insert_dict(sql_file, data):
    print "sql_file: %s" % sql_file
    print "connection_options: %s" % str(connection_options)
    conn = sqlite3.connect(sql_file, **connection_options)
    c = conn.cursor()

    base_command = "insert into articles("
    for field in fields:
        base_command += field[0] + ","
    base_command = base_command[:-1] + ") values ("
    base_command += "?,"*len(fields)
    base_command = base_command[:-1] + ")"

    dups = []
    
    for entry in data:
        command = base_command
        opts = []
        for field in fields:
            opts.append(entry[field[0]])
        try:
            c.execute(command, opts)
        except sqlite3.IntegrityError:
            dups.append(entry['url'])
            
    conn.commit()
    print "Tried adding %s entries, %s of those were duplicates" % (len(data), len(dups))
    print "Duplicates: %s" % dups
    
def convert_pickle(sql_file, pickle_file):
    data = pickle.load(open(pickle_file))
    insert_dict(sql_file, data)

if __name__ == "__main__":
    import sys
    
    create_sqlite(sys.argv[1])
    convert_pickle(sys.argv[1], sys.argv[2])
    
