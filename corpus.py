"""Seed corpus. Every sentence must parse under the current grammar."""

CORPUS = [
    "the cat sat",
    "the dog sat",
    "the cat sits",
    "the dog sits",
    "a cat sat",
    "a dog sits",
    "the big cat sat",
    "the small dog sits",
    "the cat sat on the mat",
    "the cat sat in the mat",
    "the cat sat on a mat",
    "the dog sat on the mat",
    "the big cat sat on the small mat",
    "the small dog sits on the big mat",
    "a cat sat on the mat",
    "the cat chased the dog",
    "the dog chased the cat",
]


# Sentences the grammar cannot parse. For gap analysis demo. Not used by learning.
GAPS = [
    "the big red cat sat",         # needs det adj adj noun → NP
    "the cat sat the dog",         # sat is intransitive; can't take an object
]
