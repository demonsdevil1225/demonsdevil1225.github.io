import re

# Read the raw extracted content
with open("45_sex_positions.txt", "r", encoding="utf-8") as f:
    content = f.read()

# Find all positions using regex
# Pattern: POSITION X followed by Name: ...
position_pattern = r'POSITION (\d+)\nName: Sex Position: ([^\n]+)'
positions_found = re.findall(position_pattern, content)

# Also find "Also Known As" after each position
aka_pattern = r'POSITION (\d+)\nName: Sex Position: [^\n]+\nDetails: @[^\n]*\nAlso Known As: Also known as:([^\n]+)'
aka_found = re.findall(aka_pattern, content)

# Find Benefits
benefits_pattern = r'POSITION (\d+)\nName: Sex Position: [^\n]+\nDetails: @[^\n]*\n(?:Also Known As: Also known as:[^\n]+\n)?Benefits: Benefits:([^\n]+)'
benefits_found = re.findall(benefits_pattern, content)

# Create dictionaries for easy lookup
aka_dict = {int(k): v.strip() for k, v in aka_found}
benefits_dict = {int(k): v.strip() for k, v in benefits_found}

# Write cleaned output
with open("45_sex_positions_clean.txt", "w", encoding="utf-8") as f:
    f.write("=" * 70 + "\n")
    f.write("45 SEX POSITIONS - NAME, ALSO KNOWN AS & BENEFITS\n")
    f.write("Source: Men's Health\n")
    f.write("=" * 70 + "\n\n")
    
    for num, name in positions_found:
        num = int(num)
        f.write(f"#{num:02d}. {name.upper()}\n")
        f.write("-" * 50 + "\n")
        
        if num in aka_dict:
            f.write(f"Also Known As: {aka_dict[num]}\n")
        
        if num in benefits_dict:
            f.write(f"Benefits: {benefits_dict[num]}\n")
        
        if num not in aka_dict and num not in benefits_dict:
            f.write("(See full description in source)\n")
        
        f.write("\n")
    
    f.write("=" * 70 + "\n")
    f.write(f"Total Positions Listed: {len(positions_found)}\n")
    f.write("=" * 70 + "\n")

print(f"Extracted {len(positions_found)} positions")
print(f"Found {len(aka_dict)} 'Also Known As' entries")
print(f"Found {len(benefits_dict)} 'Benefits' entries")
