from app import create_app

deadline_app = create_app()

if __name__ == '__main__':
    deadline_app.run(debug=True)