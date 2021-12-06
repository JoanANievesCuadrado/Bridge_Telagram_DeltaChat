import db
from models import Teacher, Student, GroupDelta, GroupsT, UserDelta, UserT

session = db.Session_factory()

if __name__ == '__main__':
    db.Base.metadata.create_all(db.engine)