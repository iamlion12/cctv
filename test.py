a = [0,0,0,0,0,
     1,0,0,0,0,
     1,1,1,1,1,
     1,1,1,1,1,
     1,1,1,1,1,
     1,1,1,1,1,
     1,1,1,1,1,
     1,1,1,1,1,
     1,0,0,0,0,
     0,0,0,0,0]

def select(l, step = 5):

    for i in range(0, len(l), step):
        if l[i:i+step].count(1) > l[i:i+step].count(0):
            if i+step < len(l):
                for j in range(i, i+step): l[j] = 1
            else:
                for j in range(i, len(l)): l[j] = 1
        else:
            if i+step < len(l):
                for j in range(i, i+step): l[j] = 0
            else:
                for j in range(i, len(l)): l[j] = 0
    return l

a = select(a)

def find_time(l, end = 0):

    time = []

    while True:
        try:
            start = end + l[end:].index(1)
            print("start ", start)
            try:
                end = start + l[start:].index(0)
                time.append((start, end))
                print("end ", end)

            except ValueError:
                time.append((start, len(l)))
                break
        except ValueError:
            break

    return time

print(a)
for i in find_time(a):
    print(a[i[0]:i[1]])
