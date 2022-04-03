import struct

zero = b'\xc0'

class CamadaEnlace:
    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        self.callback = None
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:
    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.current_data = b''
        self.st_1 = False
        self.st_2 = False
    
    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        datagrama = bytearray(datagrama)
        datagrama_signal = []
        for i, j in enumerate(datagrama):
            if(datagrama[i] == 0xC0):
                datagrama_signal += b'\xdb\xdc' 
            elif(datagrama[i] == 0xDB):
                datagrama_signal += b'\xdb\xdd' 
            else:
                datagrama_signal += (int.to_bytes(j, length=1, byteorder="big")) 
        datagrama_signal = zero + bytearray(datagrama_signal) + zero
        self.linha_serial.enviar(datagrama_signal)

    def __raw_recv(self, dados):
        zero = 0xC0
        data_send = b''

        for i, j in enumerate(dados):
            if(j == 0xDB):
                self.st_1 = self.st_2 = True
            elif(self.st_1 and j == 0xDC):
                self.current_data += (int.to_bytes(0xC0, length=1, byteorder="big")) 
                self.st_1 = self.st_2 = False
            elif(self.st_2 and j == 0xDD):
                self.current_data += (int.to_bytes(0xDB, length=1, byteorder="big")) 
                self.st_1 = self.st_2 = False
            elif j == zero:
                self.st_1 = self.st_2 = False
                data_send = self.current_data
                if (len(data_send) != 0):
                    try:
                        self.callback(data_send)
                    except:
                        import traceback
                        traceback.print_exc()
                    self.current_data = b''
            else:
                self.current_data += (int.to_bytes(j, length=1, byteorder="big"))
