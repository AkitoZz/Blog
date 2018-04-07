num = int(input())
a = []
for i in range(num):
    a.append(input().split())
    
for i in a:
    for j in range(len(i)):
        i[j] = int(i[j])

print(a)