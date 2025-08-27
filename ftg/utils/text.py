MAX_LEN=4096
def trim(t,l=MAX_LEN):
    t=t or ''
    return t if len(t)<=l else t[:l-3]+'...'
