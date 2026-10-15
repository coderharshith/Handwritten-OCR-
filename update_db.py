from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql+mysqlconnector://root:@localhost/evaluation')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # We assume Aarav Sharma has id = 1.
    student_id = 1
    
    # 1. Clear existing dummy answers and results
    db.execute(text("DELETE FROM student_results WHERE student_id = :id"), {"id": student_id})
    db.execute(text("DELETE FROM student_answers WHERE student_id = :id"), {"id": student_id})
    
    # 2. Insert Question 1a
    q1a_num = "1a"
    q1a_text = "Explain the various factors supported for the development of block chain technology."
    q1a_ans = """Factors supporting the development of Block Chain technology.
- State Machine Replication
Block chain works as a replicated state machine - every node in the network maintains an identical copy of the state. When a new transaction is validated, all nodes apply the same state transition independently, so every honest node ends up with the same updated state. This duplication across many independent nodes is what gives blockchain its fault tolerance and consistency without a central authority.
- Consensus mechanism
Since there is no central coordinator, all participating nodes must agree on a single, valid version of the ledger. Consensus mechanisms provide the rules by which distributed, mutually distrusting nodes reach agreement on which transactions are valid and in what order they are added - solving the distributed agreement problem that earlier systems could not solve without trusted intermediaries.
- Hashcash
Originally designed as an anti-spam mechanism, Hashcash introduced the idea of "proof of work" - requiring a node to solve a computationally difficult puzzle before an action is accepted. Bitcoin adapted this concept for block mining: a miner must find a nonce such that the block's hash meets a difficulty target, making it computationally expensive to create blocks and thus securing the chain against spam attacks.
- Peer-to-peer networks
Block chain runs on a decentralized P2P network where every node can directly communicate with and relay data to, every other node - with no central server. This removes single points of control, allows nodes to broadcast transactions and blocks directly and is a key enabler of block chain decentralization.
- E-cash schemes
Early digital cash schemes explored how to create digital money with properties like anonymity and double spend prevention, but relied on a central bank. These schemes laid the conceptual groundwork that blockchain later built upon - removing the need for a central issuer by combining these ideas with consensus & P2P networking."""

    db.execute(text("INSERT INTO student_answers (student_id, question_number, answer_text) VALUES (:s, :q, :a)"), {"s": student_id, "q": q1a_num, "a": q1a_ans})
    db.execute(text("INSERT INTO student_results (student_id, question_number, question_text, student_answer, marks_awarded, max_marks, summary) VALUES (:s, :q, :qt, :sa, :m, :mx, :sum)"), {
        "s": student_id,
        "q": q1a_num,
        "qt": q1a_text,
        "sa": q1a_ans,
        "m": 10,
        "mx": 10,
        "sum": "Excellent answer. Covered State Machine Replication, Consensus, Hashcash, P2P Networks, and E-cash schemes accurately."
    })

    # 3. Insert Question 1b
    q1b_num = "1b"
    q1b_text = "Explain any three consensus algorithms used in block chain technology."
    q1b_ans = """Any three consensus algorithms.
- Proof of Work (PoW)
Miners compete to solve a computationally intensive cryptographic puzzle. The first to solve it broadcasts the block, and other nodes verify it easily. It is a secure but energy-intensive and slow.
- Proof of Stake (PoS)
Instead of computational work, validators are chosen to create the next block based on the amount of cryptocurrency they "stake" as collateral. Higher stake generally increase the chance of being selected. It is far more energy-efficient than PoW and discourages malicious behavior since a validator risks losing their stake.
- Delegated Proof of Stake (DPoS)
Token holders vote to elect a limited set of "delegates" or witnesses who are responsible for validating transactions and producing blocks on their behalf. This makes the system faster and more scalable than plain PoS, through it introduces a degree of centralization since only elected delegates can produce blocks."""

    db.execute(text("INSERT INTO student_answers (student_id, question_number, answer_text) VALUES (:s, :q, :a)"), {"s": student_id, "q": q1b_num, "a": q1b_ans})
    db.execute(text("INSERT INTO student_results (student_id, question_number, question_text, student_answer, marks_awarded, max_marks, summary) VALUES (:s, :q, :qt, :sa, :m, :mx, :sum)"), {
        "s": student_id,
        "q": q1b_num,
        "qt": q1b_text,
        "sa": q1b_ans,
        "m": 6,
        "mx": 6,
        "sum": "Perfect explanation of PoW, PoS, and DPoS with clear distinctions."
    })

    # 4. Insert Question 1c
    q1c_num = "1c"
    q1c_text = "What are the limitations of block chain technology? Explain in brief."
    q1c_ans = """Limitations of Block Chain technology.
- Scalability.
Block chain process transactions much slower than centralized system because every node must validate & store every transaction.
- Adaptability.
Once a block chain protocol is deployed and widely adopted, changing its core rules is difficult. upgrades often require consensus among large decentralized community.
- Regulation
Because blockchain is decentralized and often operates across national borders, it doesn't fit neatly into existing legal and regulatory frameworks.
- Privacy
While block chain offers pseudonymity all transactions are permanently recorded on a public transparent ledger. This means transaction pattern can potentially be traced back to real identities which is a concern for users who want genuine privacy."""

    db.execute(text("INSERT INTO student_answers (student_id, question_number, answer_text) VALUES (:s, :q, :a)"), {"s": student_id, "q": q1c_num, "a": q1c_ans})
    db.execute(text("INSERT INTO student_results (student_id, question_number, question_text, student_answer, marks_awarded, max_marks, summary) VALUES (:s, :q, :qt, :sa, :m, :mx, :sum)"), {
        "s": student_id,
        "q": q1c_num,
        "qt": q1c_text,
        "sa": q1c_ans,
        "m": 4,
        "mx": 4,
        "sum": "Provided 4 excellent points: Scalability, Adaptability, Regulation, and Privacy."
    })

    db.commit()
    print("Successfully updated database with the PDF Blockchain data!")

except Exception as e:
    db.rollback()
    print("Error:", e)
finally:
    db.close()
