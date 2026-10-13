with open('app/services/correlation/framework.py', 'r') as f:
    content = f.read()

# Find CorrelationMatch class
start = content.find('class CorrelationMatch')
end = content.find('\\n\\nclass ', start)
if end < 0:
    end = start + 2000
print("=== CorrelationMatch class ===")
print(content[start:end])

# Find build_correlation_match
start2 = content.find('def build_correlation_match')
end2 = content.find('\\n\\ndef ', start2)
if end2 < 0:
    end2 = start2 + 2000
print("\\n=== build_correlation_match function ===")
print(content[start2:end2])