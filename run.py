from app import create_app

app = create_app()

if __name__ == "__main__":
    # 0.0.0.0 allows a phone on the same private Wi-Fi network to connect.
    app.run(host="0.0.0.0", port=5050, debug=True)
