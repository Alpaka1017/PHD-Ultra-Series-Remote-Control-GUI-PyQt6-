import serial
import binascii

ser = serial.Serial(port='COM5', baudrate=9600, timeout=0)
ser.flushInput()
ser.flushOutput()
response = b''  # 缓存区
response_multiline = []
# ser.write('@cat\r\n'.encode('utf-8'))
commands = "ivolume\r\nitime\r\ncrate\r\nirate\r\n@cat\r\n@cat\r\n@cat\r\n"
ser.write(commands.encode('utf-8'))
while True:
    line = ser.readline()
    # if line and line != b'':
    #     print("line", line)
    if line and line != b'':
        response += line
        # print(response)
        # print(len(response_multiline), len(commands.strip().split('\r\n')))
        # if len(response_multiline) < len(commands.strip().split('\r\n')):
        if line.endswith((b':', b'<', b'>', b'*', b'T*')):
            response_multiline.append(response)
            print(response_multiline)
            response = b''
            if ser.readline():
                continue
            else:
                break

    # elif line == b'':
    #     ser.close()
    #     break
    # else:
    #     ser.close()
    #     break
# print(f'Sent commands: \r\n{commands}')
# print('Response undecoded: ', response, '\n')
print(item for item in response_multiline)
# print('Response decoded: ', response.decode('utf-8'))
# print('If decoded response ends with ":"? ', response.decode('utf-8').endswith(':'))

# print('Port closed? -->', not ser.isOpen())
