from sqlalchemy import create_engine, text

engine = create_engine('mysql+mysqlconnector://root:@localhost/evaluation')
with engine.connect() as conn:
    conn.execute(text("UPDATE students SET usn = REPLACE(usn, 'VV', 'GW') WHERE usn LIKE '%VV%'"))
    conn.execute(text("UPDATE students SET username = REPLACE(username, 'VV', 'GW') WHERE username LIKE '%VV%'"))
    conn.commit()
    
    res = conn.execute(text("SELECT id, usn, username FROM students")).fetchall()
    for r in res:
        print(f"ID: {r[0]}, USN: {r[1]}, Username: {r[2]}")
