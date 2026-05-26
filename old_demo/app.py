from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>Chao mung den voi ITviec Mini!</h1>
    <p>He thong De xuat Khoa hoc cua Duong dang duoc xay dung...</p>
    """

if __name__ == "__main__":
    app.run(debug=True)