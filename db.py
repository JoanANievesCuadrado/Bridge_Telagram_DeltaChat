from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

if isfile('db_config.txt'):
    lines = open('db_config.txt').readlines()
    for line in lines:
        if re.match(r'DB_USERNAME:([a-zA-Z0-9_.+-@]+)', line):
            DB_USERNAME = re.match(r'DB_USERNAME::([a-zA-Z0-9_.+-@]+)', line).group(1).strip()
        elif re.match(r'DB_PASSWORD:([a-zA-Z0-9_.+-@]+)', line):
            DB_PASS = re.match(r'DB_PASSWORD:([a-zA-Z0-9_.+-@]+)', line).group(1).strip()
        elif re.match(r'DB_URL:([a-zA-Z0-9_.+-@]+)', line):
            DB_URL = re.match(r'DB_URL:([a-zA-Z0-9_.+-@]+)', line).group(1).strip()
        elif re.match(r'DB_PORT:(\d+)', line):
            DB_PORT = re.match(r'DB_PORT:(\d+)', line).group(1).strip()
        elif re.match(r'DB_NAME:([a-zA-Z0-9_.+-@]+)', line):
            DB_NAME = re.match(r'DB_NAME:([a-zA-Z0-9_.+-@]+)', line).group(1).strip()
        else:
            print('Necesita configurar el archivo db_config.txt')
            exit()
else:
    print('Falta el archivo db_config.txt')
    exit()

engine = create_engine(f'postgresql://{DB_USERNAME}:{DB_PASS}@{DB_URL}:{DB_PORT}/{DB_NAME}')
Session_factory = sessionmaker(bind=engine)
Base = declarative_base()