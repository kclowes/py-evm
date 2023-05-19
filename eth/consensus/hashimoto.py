import codecs
from Crypto.Hash import keccak as pc_keccak
import sha3

from eth_hash.auto import keccak
import copy


WORD_BYTES = 4  # bytes in word
DATASET_BYTES_INIT = 2**30  # bytes in dataset at genesis
DATASET_BYTES_GROWTH = 2**23  # dataset growth per epoch
CACHE_BYTES_INIT = 2**24  # bytes in cache at genesis
CACHE_BYTES_GROWTH = 2**17  # cache growth per epoch
CACHE_MULTIPLIER = 1024  # Size of the DAG relative to the cache
EPOCH_LENGTH = 30000  # blocks per epoch
MIX_BYTES = 128  # width of mix
HASH_BYTES = 64  # hash length in bytes
DATASET_PARENTS = 256  # number of parents of each dataset element
CACHE_ROUNDS = 3  # number of rounds in cache production
ACCESSES = 64  # number of accesses in hashimoto loop

FNV_PRIME = 0x01000193


def fnv(v1: int, v2: int):
    return ((v1 * FNV_PRIME) ^ v2) % 2**32


# def decode_int(s):
#     return int(s[::-1].encode("hex"), 16) if s else 0


def encode_int(num):
    return hex(num)[2::-1]  # strip off '0x', and reverse
    # a = "%x" % num  # turn into hex
    # if num == 0:
    #     return ""
    # else:
    #     # codecs.decode(a, 'hex') returns b'('
    #     # but need a string
    #     # codecs.decode(b'(') returns a string: '(' rather than a bytestring
    #     return codecs.decode(codecs.decode("0" * (len(a) % 2) + a, "hex")[::-1], "hex")


def zpad(foo, length):
    return foo + "\x00" * max(0, length - len(foo))


def serialize_hash(h):
    return "".join([zpad(encode_int(x), 4) for x in h])


# def deserialize_hash(h):
#     return [decode_int(h[i : i + WORD_BYTES]) for i in range(0, len(h), WORD_BYTES)]


# def hash_words(h, sz, x):
#     if isinstance(x, list):
#         x = serialize_hash(x)
#     y = h(x)
#     return deserialize_hash(y)


def serialize_cache(ds):
    return "".join([serialize_hash(h) for h in ds])


def sha3_512(seed):
    hasher = pc_keccak.new(data=seed, digest_bits=512)
    return hasher.digest()


def sha3_256(seed):
    hasher = pc_keccak.new(data=seed, digest_bits=256)
    return hasher.digest()


# def sha3_256(seed):
#     k = sha3.keccak_256()
#     k.update(seed)
#     return k.digest()


# def sha3_512(seed):
#     k = sha3.keccak_512()
#     k.update(seed)
#     return k.digest()


# def get_cache_size(block_number):
#     sz = CACHE_BYTES_INIT + CACHE_BYTES_GROWTH * (block_number // EPOCH_LENGTH)
#     sz -= HASH_BYTES
#     while not isprime(sz / HASH_BYTES):
#         sz -= 2 * HASH_BYTES
#     return sz


def isprime(x):
    for i in range(2, int(x**0.5)):
        if x % i == 0:
            return False
    return True


# def xor(a, b):
#     return a ^ b


def get_full_size(block_number):
    sz = DATASET_BYTES_INIT + DATASET_BYTES_GROWTH * (block_number // EPOCH_LENGTH)
    sz -= MIX_BYTES
    while not isprime(sz / MIX_BYTES):
        sz -= 2 * MIX_BYTES
    return sz


def generate_seedhash(block_number):
    # C code:
    # uint64_t const epochs = block_number / ETHASH_EPOCH_LENGTH;
    # for (uint32_t i = 0; i < epochs; ++i)
    # 	  SHA3_256(&ret, (uint8_t*)&ret, 32);
    # ret = ""
    # for i in range(0, epoch):
    #     ret = keccak(i)
    # breakpoint()
    # return ret
    epoch = block_number // EPOCH_LENGTH
    seed = b"\x00" * 32
    while epoch != 0:
        seed = sha3_256(seed)
        epoch -= 1
    return seed


# def generate_cache_size(block_number):
#     size = INITIAL_CACHE_SIZE + (CACHE_EPOCH_GROWTH_SIZE * epoch(block_number))
#     size -= HASH_BYTES
#     while not is_prime(size // HASH_BYTES):
#         size -= 2 * HASH_BYTES

#     return size


def xor(first_item: int, second_item: int) -> bytes:
    return bytes([a ^ b for a, b in zip(first_item, bytes(second_item))])


# def mkcache(cache_size):
def mkcache(block_number):
    cache_size = get_full_size(block_number)
    n = cache_size // HASH_BYTES
    print("mkcache n: ", n)

    seed = generate_seedhash(block_number)
    # Sequentially produce the initial dataset
    o = [sha3_512(seed)]
    # for i in range(1, n):
    for i in range(1, 1000):
        o.append(sha3_512(o[-1]))

    # Use a low-round version of randmemohash
    for _ in range(CACHE_ROUNDS):
        # for i in range(n):
        for i in range(1000):
            first_cache_item = o[i - 1 + int(n) % n]
            foo = int.from_bytes(o[i][0:4], "little")  # might be big?
            second_cache_item = foo % n
            # v = o[i][0] % n
            result = xor(first_cache_item, second_cache_item)
            o[i] = sha3_512(result)
            # o[i] = sha3_512(map(xor, o[(i - 1 + n) % n], o[v]))
    return o


def int_to_le_bytes(val):
    # I'm not sure that this is 100% right
    return val.to_bytes(HASH_BYTES, "little")


def bytes_to_int(val):
    # I'm not sure that this is 100% right
    return int.from_bytes(val, "little")


def calc_dataset_item(cache, i):
    print(len(cache))
    cache_length = len(cache)
    r = HASH_BYTES // WORD_BYTES
    # initialize the mix
    # mix = cache[i % n]
    mix = bytes_to_int(cache[i % cache_length])
    print("mix 1: ", mix)
    mix ^= i  # want to compare int to int here
    print("mix 2: ", mix)

    mix = sha3_512(int_to_le_bytes(mix))
    # mix = b"00" * 32
    print("mix 3: ", mix)
    # fnv it with a lot of random cache nodes based on i
    # for j in range(DATASET_PARENTS):
    for j in range(2):
        cache_index = fnv(i ^ j, mix[j % r])
        mix = bytes(
            fnv(bytes_to_int(mix), bytes_to_int(cache[cache_index % cache_length]))
        )
        # mix = map(fnv, mix, cache[cache_index % n])
    return sha3_512(mix)


def calc_dataset(full_size, cache):
    print("calc_dataset")
    return [calc_dataset_item(cache, i) for i in range(full_size // HASH_BYTES)]


def hashimoto(header, nonce, full_size, dataset_lookup):
    n = full_size / HASH_BYTES
    w = MIX_BYTES // WORD_BYTES  # 128 // 4 = 32
    mixhashes = MIX_BYTES // HASH_BYTES  # 128 / 64 = 2
    # combine header+nonce into a 64 byte seed
    s = sha3_512(header + nonce[::-1])
    # start the mix with replicated s
    mix = []
    print("got here: 0")
    for _ in range(MIX_BYTES // HASH_BYTES):  # 2
        mix.extend(s)
    print("got here: 1")
    # mix in random dataset nodes
    # for i in range(ACCESSES):  # 64
    for i in range(2):
        p = int(fnv(i ^ s[0], mix[i % w]) % (n / mixhashes) * mixhashes)
        newdata = []
        print("got here: 2")
        for j in range(MIX_BYTES // HASH_BYTES):  # 2
            print("p + j: ", p + j)
            newdata.extend(dataset_lookup(p + j))
        # mix = map(fnv, mix, newdata)
        print("got here: 3")
        mix = bytes(fnv(bytes_to_int(mix), bytes_to_int(newdata)))
    # compress mix
    cmix = []
    print("got here: 4")
    for i in range(
        0, len(mix) - 3, 4
    ):  # the '-3' is to avoid an IndexError. It shouldn't hit the IndexError
        cmix.append(fnv(fnv(fnv(mix[i], mix[i + 1]), mix[i + 2]), mix[i + 3]))
    print("got here: 5")
    return {
        "mix digest": serialize_hash(cmix),
        # "result": serialize_hash(sha3_256(s + cmix)),
        "result": serialize_hash(sha3_256(cmix.extend(s))),
    }


def hashimoto_light(full_size, cache, header, nonce):
    b_nonce = nonce.to_bytes(8, "little")
    print("hashi light")
    return hashimoto(header, b_nonce, full_size, lambda x: calc_dataset_item(cache, x))


def hashimoto_full(full_size, dataset, header, nonce):
    return hashimoto(header, nonce, full_size, lambda x: dataset[x])
