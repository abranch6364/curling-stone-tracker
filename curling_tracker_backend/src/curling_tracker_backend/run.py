import curling_tracker_backend

if __name__ == "__main__":
    app = curling_tracker_backend.create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
