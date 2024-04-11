import subprocess as sp


def print_pdf(printer_name, filename, pages=None, color=None, orientation=None):
    command = ['lp', '-d', printer_name]
    if pages:
        command.extend(['-P', pages])
    if orientation:
        command.extend(['-o', f'orientation-requested={orientation}'])
    if color:
        command.extend(['-o', f'ColorModel={color}'])
    command.extend([filename])

    print_proc = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
    output = print_proc.communicate()
    return output
