try:
    from kivy.support import install_twisted_reactor

    install_twisted_reactor()
except:
    print('gna')

from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet.protocol import DatagramProtocol
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import ObjectProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ListProperty
from kivy.clock import Clock
import uuid
import os.path

from os import listdir

kv_path = './kv/'
for kv in listdir(kv_path):
    Builder.load_file(kv_path + kv)


class CueSysServer(protocol.Protocol):

    def __init__(self,app):
        self.app = app

    def dataReceived(self, data):
        print("received...")
        print(data)
        message = data.decode('utf-8').split('@')
        if message[0] == 'Status':
            self.app.setStatus(int(message[1]))
        elif message[0] == 'Cue':
            self.app.setCue(message[1],message[2])
        elif message[0] == 'Name':
            self.app.setName(message[1])
        #response = self.factory.app.handle_message(data)
        #if response:
        #    self.transport.write(response)

    def connectionMade(self):
        print('New Connection')
        self.transport.write(('CueSys@'+self.app.uuid+'@1.0').encode())
        self.app.connection = self
        self.app.connected = True

    def connectionLost(self, reason):
        print('connection Lost')
        self.app.connected = False

class CueSysServerFactory(protocol.ClientFactory):

    def __init__(self, app):
        self.app = app

    def buildProtocol(self, addr):
        return CueSysServer(app)


class BCastFactory(DatagramProtocol):

    def __init__(self, app):
        self.app = app

    def datagramReceived(self, data, host):
        # message from my server?
        # print("received %r from %s" % (data, host))
        # self.transport.write(data, (host, port))
        self.app.handleBCast_message(data)


class StbButton(Button):
    background_off_color_normal = ListProperty([0.5, 0.5, 0.5, 1])
    background_stb_color_normal = ListProperty([0.7, 0, 0, 1])
    background_stb_color_highlight = ListProperty([1, 0, 0, 1])
    background_go_color_normal = ListProperty([0, 0.7, 0, 1])
    background_go_color_highlight = ListProperty([0, 1, 0, 1])

    def __init__(self, **kwargs):
        super(StbButton, self).__init__(**kwargs)
        self.background_color = self.background_off_color_normal

    def setOff(self):
        self.background_color = self.background_off_color_normal
        self.text = 'No Cue'

    def setStbOn(self):
        self.background_color = self.background_stb_color_highlight
        self.text = 'Standby'

    def setStbOff(self):
        self.background_color = self.background_stb_color_normal
        self.text = 'Standby'

    def setGoOn(self):
        self.background_color = self.background_go_color_highlight
        self.text = 'GO!'

    def setGoOff(self):
        self.background_color = self.background_go_color_normal






class ClientContainer(GridLayout):
    display = ObjectProperty()


    def on_event(self, obj):
        print("Typical event from", obj.id)
        # obj.togglecolor()


    def addButton(self, name):
        elements = {}
        layout = BoxLayout(orientation='vertical', id=name)
        l = Label(text=name, font_size='15sp', size_hint_y= 5)
        btn1 = StbButton(id='Button', size_hint_y= 95)
        #btn1.bind(on_release=self.on_event)
        layout.add_widget(l)
        layout.add_widget(btn1)
        self.clients.add_widget(layout)

        elements['Layout' + name] = layout
        elements['Button'] = btn1

        return elements



class MainApp(App):
    # ------------------ Globals ----------------------
    # all my elements
    # L_X are the Layouts
    # Stb_X are the Standby buttons
    # Prs_X are the Preset Buttons
    # Go_X are the Go Buttons
    elements = {}

    display = None
    blink = {}

    # Status
    # Binary implementation
    # Position/Value
    # 1 = RedBlink
    # 2 = Red
    # 3 = yellow
    # 4 = Green
    clientstatus = {}

    # State of the Blink, so all of them are at the same time on or off
    onoff = False
    connection = False

    uuid = False
    connected = False

    # ------------------- App Stuff --------------------
    # first setup
    def build(self):
        self.title = 'CueSys'

        # get my container
        display = ClientContainer()
        self.display = display

        # add clients
        self.addClient('self')

        # setting up the blinking stuff
        blinkerevent = Clock.schedule_interval(self.blinker, 0.5)
        fname = "clientid.txt"
        if os.path.isfile(fname):
            file = open(fname, 'r')
            self.uuid = file.read()


        try:
            reactor.listenUDP(8099, BCastFactory(self))
        except:
            print('Server could not be started! Is another instance running?')

        return display


    def addClient(self, name):
        self.elements[name] = self.display.addButton(name)
        self.clientstatus[name] = 0

    def blinker(self, dt):

        if (self.clientstatus['self'] == 0) or (self.clientstatus['self'] == 4):
            self.elements['self']['Button'].setOff()
        elif self.clientstatus['self'] & 0b0001:
            if not self.onoff:
                self.elements['self']['Button'].setStbOff()
            else:
                self.elements['self']['Button'].setStbOn()
        elif self.clientstatus['self'] & 0b0010:
            self.elements['self']['Button'].setStbOn()
        elif self.clientstatus['self'] & 0b1000:
            self.elements['self']['Button'].setGoOn()

        if not self.onoff:
            self.onoff = True
        else:
            self.onoff = False
        print('mystatus '+str(self.clientstatus['self']))


    def btnPressed(self, obj):
        if self.clientstatus['self'] & 0b0001:
            self.clientstatus['self'] -= 0b0001
            self.clientstatus['self'] += 0b0010
            self.connection.transport.write(('Status@Confirmed').encode())



    # ----------------- Network Stuff -----------------------
    def handle_message(self, msg):
        msg = msg.decode('utf-8')
        self.display.mainview.text = "received:  {}\n".format(msg)
        print("received:  {}\n".format(msg))
        if msg == "ping":
            msg = "Pong"
        if msg == "plop":
            msg = "Kivy Rocks!!!"
        self.display.mainview.text += "responded: {}\n".format(msg)
        return msg.encode('utf-8')

    def setStatus(self,status):
        self.clientstatus['self'] = status

    def handleBCast_message(self, msg):

        server = msg.decode('utf-8').split('@')

        if server[0] == "CueSys" and server[2] == "1.0" and not self.connected:
            reactor.connectTCP(server[1], 8090, CueSysServerFactory(self))


if __name__ == "__main__":
    app = MainApp()
    app.run()
    fname = "clientid.txt"
    if not os.path.isfile(fname):
        text_file = open(fname, "w")
        text_file.write(str(uuid.uuid4()))
        text_file.close()
