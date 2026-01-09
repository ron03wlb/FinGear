
import os

file_path = 'docs/500_stocks.txt'
new_stocks = [
    '5306 桂盟', 
    '6782 視陽', 
    '4746 台耀', 
    '5009 榮剛', 
    '9933 中鼎', 
    '5388 中磊', 
    '2439 美律', 
    '6533 晶心科', 
    '2393 億光', 
    '6670 復盛應用'
]

def main():
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return

    # Read existing
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    existing_ids = {line.split()[0] for line in lines}
    
    # Add new if not exists
    added_count = 0
    for stock in new_stocks:
        stock_id = stock.split()[0]
        if stock_id not in existing_ids:
            lines.append(stock)
            added_count += 1
            print(f"Added: {stock}")
        else:
            print(f"Skipped (already exists): {stock}")

    # Sort
    lines.sort(key=lambda x: x.split()[0])

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    print(f"Successfully updated {file_path}. Added {added_count} stocks. Total: {len(lines)}")

if __name__ == "__main__":
    main()
