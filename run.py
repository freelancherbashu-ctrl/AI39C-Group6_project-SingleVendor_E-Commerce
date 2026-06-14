<<<<<<< HEAD
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
=======
from dotenv import load_dotenv
load_dotenv()

from app import create_app
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
    
>>>>>>> 339f6d51fc6700d7bc61af782186f4ccfaac1b31
