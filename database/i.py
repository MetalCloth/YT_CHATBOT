with open(".csv") as f:
    for i, line in enumerate(f, start=1):
        if 35310 <= i <= 35330:
            print(f"{i}: {line.strip()}")
