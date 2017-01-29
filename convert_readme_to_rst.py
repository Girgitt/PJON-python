from pypandoc import convert

read_rst = convert('./README.md', 'rst')


with open('./README.rst', 'w') as fo_h:
    fo_h.writelines(read_rst)
