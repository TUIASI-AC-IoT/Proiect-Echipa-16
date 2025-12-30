# Documentatie Client CoAP

## 1. Scopul proiectului  
 Scopul acestui proiect este implementarea unui client CoAP (Constrained Application Protocol) care permite trimiterea si accesarea unor documente de mic dimensiuni într-o arhitectură de tip remote storage.
Protocolul CoAP este conceput pentru sisteme cu resurse limitate (dispozitive IoT, senzori, microcontrolere), fiind o alternativă ușoară la HTTP, bazată pe UDP.
Clientul implementat oferă o serie de funcționalități printre care se numără:
	-încărcarea și descărcarea fișierelor,
	-crearea și ștergerea acestora,
	-navigarea în structura de directoare,
	-mutarea fișierelor între directoare
	-implementarea unei interfete prietenoase.
Comunicarea între client și server se face exclusiv prin mesaje CoAP, transmise prin socket-uri UDP. 

## 2. Formatarea pachetelor  
Comunicarea între client și server se face exclusiv prin mesaje CoAP, transmise prin socket-uri UDP.
```text
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |Ver| T |  TKL  |      Code     |          Message ID           |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |   Token (if any, TKL bytes) ...
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |   Options (if any) ...
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |1 1 1 1 1 1 1 1|    Payload (if any) ...
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
Header:
	-este alcătuit din 4 octeți
Token:
	-rolul token-ului este acela de a corela cererile cu răspunsurile. Astfel, cererea
respectiv răspunsul primit vor avea același token.
Options:
	-conțin informații suplimentare despre mesaj, cum ar fi tipul de conținut, calea resursei, dimensiunea datelor sau parametri specifici aplicației.
Payload:
	-aici este situat mesajul propriu-zis

Pachete proprietare (pentru aplicație)
Tip				Descriere			Conținut Payload
FILE_UPLOAD		Client → Server		Header CoAP (POST) + nume fișier + conținut fișier
FILE_DOWNLOAD	Client → Server		Header CoAP (GET) + calea fișierului
FILE_DELETE		Client → Server		Header CoAP (DELETE) + calea fișierului
FILE_MOVE		Client → Server		Header CoAP (CUSTOM/MOVE) + calea sursă + calea destinație
DIR_LIST		Client → Server		Header CoAP (GET) + calea directorului
```
