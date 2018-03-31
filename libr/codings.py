import struct


def compress_vb(nums, sort=False):
    s = ''
    if sort:
        nums = [nums[0]] + [nums[i] - nums[i-1] for i in range(1, len(nums))]
    for i, num in enumerate(nums):
        decomp = []
        while num > 0:
            decomp.append(num % 128)
            num /= 128
        if len(decomp) == 0:
            decomp.append(0)
        decomp[0] |= 1 << 7
        for part in decomp[::-1]:
            s += struct.pack('B', part)
    return s


# return decompress of byte string
def decompress_vb(s, sort=False):
    nums = []
    num = 0
    for byte in s:
        if struct.unpack('B', byte)[0] >= 128:
            rest = struct.unpack('B', byte)[0] & 127
            num *= 128
            num += rest
            nums.append(num)
            num = 0
        else:
            rest = struct.unpack('B', byte)[0]
            num *= 128
            num += rest
    
    if sort:
        for i in range(1, len(nums)):
            nums[i] += nums[i-1]      
    return nums


def compress_s9(nums, sort=False):
    var = {28: 0, 14: 1, 9: 2, 7: 3, 5: 4, 4: 5, 3: 6, 2: 7, 1: 8}

    def pack(nums):
        x = var[len(nums)] << 28
        for i in range(len(nums)):
            x |= nums[i] << (28 - (i + 1) * (28 / len(nums)))
        return struct.pack('I', x)
                    
    s = ""
    min_bites_size = 0
    segment = []
    if sort:
        nums = [nums[0]] + [nums[i] - nums[i-1] for i in range(1, len(nums))]
        
    for num in nums:
        rang = min_bites_size
        while num > (1 << rang) - 1:
            rang += 1
        
        if (len(segment) + 1) * rang <= 28:
            segment.append(num)
            min_bites_size = rang
        else:
            if var.get(len(segment), None) is None:
                segment += [0]*(28 / min_bites_size - len(segment)) 
            s += pack(segment)
            segment = [num]
            min_bites_size = rang
            
    if len(segment) != 0:
        if var.get(len(segment), None) is None:
            segment += [0]*(28 / min_bites_size - len(segment))
        s += pack(segment)
    return s


def decompress_s9(s, sort=False):
    var = {0: 28, 1: 14, 2: 9, 3: 7, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
    nums = []
    for i in range(len(s) / 4):
        segment = struct.unpack('I', s[i*4:(i+1)*4])[0]
        count = var[(segment >> 28) & 15]
        length = 28 / count
        for j in range(count):
            num = (segment >> (28 - (j + 1) * length)) & ((1 << length) - 1)
            if num != 0:
                nums.append((segment >> (28 - (j + 1) * length)) & ((1 << length) - 1))
    if sort:
        for i in range(1, len(nums)):
            nums[i] += nums[i-1]      
    return nums
