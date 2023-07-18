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
        self.buffer = b''

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        # Realiza o escape dos bytes 0xC0 e 0xDB
        datagrama = datagrama.replace(b'\xDB', b'\xDB\xDD')
        datagrama = datagrama.replace(b'\xC0', b'\xDB\xDC')

        # Adiciona o byte especial 0xC0 no início e no fim do quadro
        quadro = b'\xC0' + datagrama + b'\xC0'
        
        # Envia o quadro pela linha serial
        self.linha_serial.enviar(quadro)

    def __raw_recv(self, dados):
        # Adiciona os dados recebidos ao buffer
        self.buffer += dados

        # Separa os dados em quadros completos e o restante do buffer
        quadros, self.buffer = self.buffer.split(b'\xc0')[:-1], self.buffer.split(b'\xc0')[-1]

        # Processa cada quadro completo
        for quadro in quadros:
            # Remove quadros vazios
            if quadro != b'':
                # Remove as sequências de escape
                datagrama = self.desescape(quadro)

                try:
                    # Chama o callback com o datagrama original
                    self.callback(datagrama)
                except:
                    import traceback
                    traceback.print_exc()

    def desescape(self, quadro):
        # Realiza o unescape dos bytes de escape
        quadro = quadro.replace(b'\xDB\xDC', b'\xC0')
        quadro = quadro.replace(b'\xDB\xDD', b'\xDB')
        return quadro