script = open('zap_log.out')
stats = { 'peers': {}}
script_text = script.read()
script.close()

for line in script_text.split('\n'):
    fields = line.split()
    print fields
    if len(fields) == 0:
        continue
    if fields[0] == 'file':
        #Transfer rate in Mbs
        size_in_bits = int(fields[2]) * 8
        size_in_megabits = float(size_in_bits) / 1000000
        stats['transfer_rate'] = size_in_megabits / float(fields[3])
        stats['filename'] = fields[1]
        #get size in megabytes from original size in bytes
        stats['size'] = float(fields[2]) / (2 ** 20)
        stats['download_time'] = float(fields[3])
    else:
        if fields[2] in stats['peers']:
            stats['peers'][fields[2]].append(fields)
        else:
            stats['peers'][fields[2]] = [fields]

print stats
