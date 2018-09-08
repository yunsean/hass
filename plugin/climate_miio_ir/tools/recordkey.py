from miio import AirConditioningCompanion, DeviceException
import time

xiaomi = AirConditioningCompanion("YOUR IP", "YOUR TOKEN")
minTemp = 18
maxTemp = 30

result = ""
def prompt(msg):
    while True:
        str = input(msg)
        str = str.lower()
        if str == 'y' or str == 'yes':
            return True
        if str == 'n' or str == 'no':
            return False
        if str == 'r' or str == 'p':
            print(result)

def readKey():
    while True:
        xiaomi.send("start_ir_learn", [30])
        loop = 0
        while xiaomi.send("get_ir_learn_result", []) == ['(null)'] and loop < 15:
            time.sleep(1)
            loop = loop + 1
        if loop >= 15:
            continue
        ir_code = "".join(xiaomi.send("get_ir_learn_result", []))
        if ir_code:
            code_list = list(ir_code)
            code_list[14:26] = '94701FFF96FF'
            sub = ir_code[34:36]
            check = hex(int(sub, 16) - 68)[2:]
            if len(check) == 1:
                check = '0' + check
            code_list[33:36] = '7' + check
            ir_code = ''.join(code_list)
            return ir_code

result = ""
print("【录制关机指令】现在，请先用手掌捂住遥控器的发射灯，并将空调模式调整为通风模式（风速Auto，摆风关闭），然后松开手掌，并按下关闭空调：")
result = result + "      - close:" + readKey() + "\n"

if prompt("需要录制离家模式指令么？"):
    print("【录制离家模式（开）指令】请用手掌捂住遥控器的发射灯，调整离家模式为关，松开手掌，并按下离家模式按钮：")
    result = result + "      - away-mode-on:" + readKey() + "\n"
    print("【录制离家模式（关）指令】请再按下离家模式按钮：")
    result = result + "      - away-mode-off:" + readKey() + "\n"

if prompt("需要录制Hold模式指令么？"):
    print("【录制Hold模式（开）指令】请用手掌捂住遥控器的发射灯，调整Hold模式为关，松开手掌，并按下Hold模式按钮：")
    result = result + "      - hold-mode-on:" + readKey() + "\n"
    print("【录制Hold模式（关）指令】请再按下Hold模式按钮：")
    result = result + "      - hold-mode-off:" + readKey() + "\n"

if prompt("需要录制通风模式（摆风关闭）的系列指令么？"):
    print("【录制通风模式（风速Auto，摆风关闭）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为通风，风速状态Auto，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - ventilate-auto-off:" + readKey() + "\n"
    print("【录制通风模式（风速低，摆风关闭）指令】请再按下遥控器的风速按钮：")
    result = result + "      - ventilate-slow-off:" + readKey() + "\n"
    print("【录制通风模式（风速中，摆风关闭）指令】请按下遥控器的风速按钮：")
    result = result + "      - ventilate-middle-off:" + readKey() + "\n"
    print("【录制通风模式（风速高，摆风关闭）指令】请再按下遥控器的风速按钮：")
    result = result + "      - ventilate-high-off:" + readKey() + "\n"
    print("【录制通风模式（风速静音，摆风关闭）指令】请再按下遥控器的风速按钮：")
    result = result + "      - ventilate-quiet-off:" + readKey() + "\n"

if prompt("需要录制通风模式（摆风开启）的系列指令么？"):
    print("【录制通风模式（风速Auto，摆风开启）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为通风，风速状态Auto，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - ventilate-auto-on:" + readKey() + "\n"
    print("【录制通风模式（风速低，摆风开启）指令】请再按下遥控器的风速按钮：")
    result = result + "      - ventilate-slow-on:" + readKey() + "\n"
    print("【录制通风模式（风速中，摆风开启）指令】请按下遥控器的风速按钮：")
    result = result + "      - ventilate-middle-on:" + readKey() + "\n"
    print("【录制通风模式（风速高，摆风开启）指令】请再按下遥控器的风速按钮：")
    result = result + "      - ventilate-high-on:" + readKey() + "\n"
    print("【录制通风模式（风速静音，摆风开启）指令】请再按下遥控器的风速按钮：")
    result = result + "      - ventilate-quiet-on:" + readKey() + "\n"

if prompt("需要录制制冷模式（风速自动，摆风关闭）的系列指令么？"):
    print("【录制制冷模式（风速自动，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为自动，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-auto-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速自动，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-auto-off-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制冷模式（风速低，摆风关闭）的系列指令么？"):
    print("【录制制冷模式（风速低，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为低，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-low-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速低，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-low-off-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制冷模式（风速中，摆风关闭）的系列指令么？"):
    print("【录制制冷模式（风速中，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为中，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-middle-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速中，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-middle-off-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制冷模式（风速高，摆风关闭）的系列指令么？"):
    print("【录制制冷模式（风速高，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为高，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-high-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速高，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-high-off-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制冷模式（风速静音，摆风关闭）的系列指令么？"):
    print("【录制制冷模式（风速静音，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为静音，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-quiet-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速静音，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-quiet-off-" + str(temp) + ":" + readKey() + "\n"
    
if prompt("需要录制制冷模式（风速自动，摆风开启）的系列指令么？"):
    print("【录制制冷模式（风速自动，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为自动，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-auto-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速自动，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-auto-on-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制冷模式（风速低，摆风开启）的系列指令么？"):
    print("【录制制冷模式（风速低，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为低，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-low-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速低，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-low-on-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制冷模式（风速中，摆风开启）的系列指令么？"):
    print("【录制制冷模式（风速中，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为中，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-middle-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速中，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-middle-on-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制冷模式（风速高，摆风开启）的系列指令么？"):
    print("【录制制冷模式（风速高，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为高，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-high-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速高，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-high-on-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制冷模式（风速静音，摆风开启）的系列指令么？"):
    print("【录制制冷模式（风速静音，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制冷模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制冷，温度为" + str(minTemp) + "度，风速状态为静音，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - cool-quiet-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制冷模式（风速静音，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - cool-quiet-on-" + str(temp) + ":" + readKey() + "\n"

print("开始录制制热模式的系列指令，如果你的空调支持电辅加热，请按照后续操作关闭电辅加热。")
if prompt("需要录制制热模式（风速自动，摆风关闭）的系列指令么？"):
    print("【录制制热模式（风速自动，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，关闭电辅加热，温度为" + str(minTemp) + "度，风速状态为自动，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-auto-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速自动，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-auto-off-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制热模式（风速低，摆风关闭）的系列指令么？"):
    print("【录制制热模式（风速低，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(minTemp) + "度，风速状态为低，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-low-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速低，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-low-off-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制热模式（风速中，摆风关闭）的系列指令么？"):
    print("【录制制热模式（风速中，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(minTemp) + "度，风速状态为中，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-middle-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速中，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-middle-off-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制热模式（风速高，摆风关闭）的系列指令么？"):
    print("【录制制热模式（风速高，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(minTemp) + "度，风速状态为高，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-high-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速高，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-high-off-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制热模式（风速静音，摆风关闭）的系列指令么？"):
    print("【录制制热模式（风速静音，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(minTemp) + "度，风速状态为静音，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-quiet-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速静音，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-quiet-off-" + str(temp) + ":" + readKey() + "\n"

if prompt("需要录制制热模式（风速自动，摆风开启）的系列指令么？"):
    print("【录制制热模式（风速自动，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(minTemp) + "度，风速状态为自动，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-auto-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速自动，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-auto-on-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制热模式（风速低，摆风开启）的系列指令么？"):
    print("【录制制热模式（风速低，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(minTemp) + "度，风速状态为低，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-low-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速低，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-low-on-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制热模式（风速中，摆风开启）的系列指令么？"):
    print("【录制制热模式（风速中，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(minTemp) + "度，风速状态为中，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-middle-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速中，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-middle-on-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制热模式（风速高，摆风开启）的系列指令么？"):
    print("【录制制热模式（风速高，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(minTemp) + "度，风速状态为高，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-high-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速高，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-high-on-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制制热模式（风速静音，摆风开启）的系列指令么？"):
    print("【录制制热模式（风速静音，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(minTemp) + "度，风速状态为静音，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - heat-quiet-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制制热模式（风速静音，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - heat-quiet-on-" + str(temp) + ":" + readKey() + "\n"

if prompt("需要录制电辅加热指令么？需要你开启电辅加热并重新进行刚才的制热录制流程。"):
    if prompt("需要录制制热模式（风速自动，摆风关闭）的系列指令么？"):
        print("【录制制热模式（风速自动，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，开启电辅加热，温度为" + str(
            minTemp) + "度，风速状态为自动，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-auto-off-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速自动，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-auto-off-" + str(temp) + ":" + readKey() + "\n"
    if prompt("需要录制制热模式（风速低，摆风关闭）的系列指令么？"):
        print("【录制制热模式（风速低，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(
            minTemp) + "度，风速状态为低，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-low-off-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速低，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-low-off-" + str(temp) + ":" + readKey() + "\n"
    if prompt("需要录制制热模式（风速中，摆风关闭）的系列指令么？"):
        print("【录制制热模式（风速中，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(
            minTemp) + "度，风速状态为中，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-middle-off-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速中，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-middle-off-" + str(temp) + ":" + readKey() + "\n"
    if prompt("需要录制制热模式（风速高，摆风关闭）的系列指令么？"):
        print("【录制制热模式（风速高，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(
            minTemp) + "度，风速状态为高，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-high-off-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速高，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-high-off-" + str(temp) + ":" + readKey() + "\n"
    if prompt("需要录制制热模式（风速静音，摆风关闭）的系列指令么？"):
        print("【录制制热模式（风速静音，摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(
            minTemp) + "度，风速状态为静音，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-quiet-off-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速静音，摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-quiet-off-" + str(temp) + ":" + readKey() + "\n"

    if prompt("需要录制制热模式（风速自动，摆风开启）的系列指令么？"):
        print("【录制制热模式（风速自动，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(
            minTemp) + "度，风速状态为自动，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-auto-on-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速自动，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-auto-on-" + str(temp) + ":" + readKey() + "\n"
    if prompt("需要录制制热模式（风速低，摆风开启）的系列指令么？"):
        print("【录制制热模式（风速低，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(
            minTemp) + "度，风速状态为低，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-low-on-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速低，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-low-on-" + str(temp) + ":" + readKey() + "\n"
    if prompt("需要录制制热模式（风速中，摆风开启）的系列指令么？"):
        print("【录制制热模式（风速中，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(
            minTemp) + "度，风速状态为中，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-middle-on-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速中，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-middle-on-" + str(temp) + ":" + readKey() + "\n"
    if prompt("需要录制制热模式（风速高，摆风开启）的系列指令么？"):
        print("【录制制热模式（风速高，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(
            minTemp) + "度，风速状态为高，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-high-on-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速高，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-high-on-" + str(temp) + ":" + readKey() + "\n"
    if prompt("需要录制制热模式（风速静音，摆风开启）的系列指令么？"):
        print("【录制制热模式（风速静音，摆风开启，" + str(minTemp) + "度）指令】接下来开始录制制热模式的指令，请用手掌捂住遥控器的发射灯，调解模式为制热，温度为" + str(
            minTemp) + "度，风速状态为静音，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
        result = result + "      - heat-quiet-on-" + str(minTemp) + ":" + readKey() + "\n"
        for temp in range(minTemp + 1, maxTemp + 1):
            print("【录制制热模式（风速静音，摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
            result = result + "      - heat-quiet-on-" + str(temp) + ":" + readKey() + "\n"

if prompt("需要录制除湿模式（摆风关闭）的系列指令么？"):
    print("【录制除湿模式（摆风关闭，" + str(minTemp) + "度）指令】接下来开始录制除湿模式的指令，请用手掌捂住遥控器的发射灯，调解模式为除湿，温度为" + str(minTemp) + "度，摆风关闭，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - dehumidify-off-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制除湿模式（摆风关闭，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - dehumidify-off-" + str(temp) + ":" + readKey() + "\n"
if prompt("需要录制除湿模式（摆风开启）的系列指令么？"):    
    print("【录制除湿模式（摆风开启，" + str(minTemp) + "度）指令】接下来开始录制除湿模式的指令，请用手掌捂住遥控器的发射灯，调解模式为除湿，温度为" + str(minTemp) + "度，摆风开启，然后按下关闭按钮切换为关闭状态，然后松开手掌，并按下开机按钮：")
    result = result + "      - dehumidify-on-" + str(minTemp) + ":" + readKey() + "\n"
    for temp in range(minTemp+1, maxTemp+1):
        print("【录制除湿模式（摆风开启，" + str(temp) + "度）指令】按下温度+按钮：")
        result = result + "      - dehumidify-on-" + str(temp) + ":" + readKey() + "\n"

print(result)
