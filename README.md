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
```
**Header**:  
&nbsp;&nbsp;&nbsp;&nbsp;-este alcătuit din 4 octeți  
**Token**:  
&nbsp;&nbsp;&nbsp;&nbsp;-rolul token-ului este acela de a corela cererile cu răspunsurile. Astfel, cererea
respectiv răspunsul primit vor avea același token.  
**Options**:  
&nbsp;&nbsp;&nbsp;&nbsp;-conțin informații suplimentare despre mesaj, cum ar fi tipul de conținut, calea resursei, dimensiunea datelor sau parametri specifici aplicației.  
**Payload**:  
&nbsp;&nbsp;&nbsp;&nbsp;-aici este situat mesajul propriu-zis

**Pachete proprietare (pentru aplicație)**  
```text
Tip			Descriere			Conținut Payload
FILE_UPLOAD		Client → Server		Header CoAP (POST) + nume fișier + conținut fișier
FILE_DOWNLOAD	        Client → Server		Header CoAP (GET) + calea fișierului
FILE_DELETE		Client → Server		Header CoAP (DELETE) + calea fișierului
FILE_MOVE		Client → Server		Header CoAP (CUSTOM/MOVE) + calea sursă + calea destinație
DIR_LIST		Client → Server		Header CoAP (GET) + calea directorului
```
## 3. Transmiterea mesajelor

În cadrul CoAP există 4 tipuri de mesaje: *Confirmable* (CON),*Non-confirmable* (NON), *Acknowledge* (ACK) și *Reset* (RST):  
1. Confirmable (CON):
	- este trimis până la primirea unui mesaj de tipul ACK sau RST;
	- cere trimiterea unui mesaj de tipul ACK sau RST, acestea din urmă trebuind să aibă același ID.
2. Non-confirmable (NON):
	- trimiterea lui nu necesită un mesaj de tip ACK sau RST.
3. Acknowledge (ACK):
	- nu indică succesul sau reușita unei cereri, arată doar faptul că cererea a ajuns la endpoint.
4. Reset (RST):
	- indică primirea unei cereri (CON sau NON) dar anumite detalii necesare lipsesc.

## 4. Operatiuni specifice CoAP si interactiunea intre server-client
### Upload fișier (POST /upload)  
Client trimite pachet Confirmable cu cod 0.02 (POST)  
	Server salvează fișierul → trimite ACK 2.01 Created  
	Payload: [path] + [file content]   
Client:
```json
        {
	  "path": "/directory/file.txt",
	  "content": "Data"
	}
```
Server:
```json
        {
	  "status": "created",
	  "path": "/directory/file.txt",
	  "size": 1024
	}
	{
	  "status": "error",
	  "message": "Unable to execute"
	}
```
### Download fișier (GET /download)  
Client trimite GET cu calea fișierului  
	Server trimite ACK 2.05 Content + payload cu fișierul  
Client:
```json
        {
	  "path": "/directory/file.txt"
	}
```
Server:
```json
        {
	  "name": "file.txt",
	  "size": 2048,
	  "content": "Data"
	}
	
	{
	  "status": "error",
	  "message": "Unable to execute"
	}
```
### Ștergere fișier (DELETE /path)
Client → Confirmable cod 0.04 (DELETE)   
	Server → ACK 2.02 Deleted  
Client:
```json
       {
	  "path": "/directory/file.txt"
	}
```
Server:
```json
       {
	  "status": "deleted",
	  "path": "/directory/file.txt"
	}
	{
	  "status": "error",
	  "message": "Unable to execute"
	}
```
### Mutare fișier (MOVE /src /dst) 
Client → Confirmable cod 0.08 (MOVE)  
	Server → ACK 2.01 Created dacă mutarea a reușit  
Client:
```json
      {
	  "source": "/directory/file_1.txt",
	  "destination": "/directory2/file_1.txt"
	}
```
Server:
```json
      {
	  "status": "moved",
	  "from": "/directory/file_1.txt",
	  "to": "/directory2/file_1.txt"
	}
	{
	  "status": "error",
	  "message": "Unable to execute"
	}
```
## 5. Threading si modelare aplicatie

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN THREAD (GUI)                        │
│  - Tkinter interface (root.mainloop())                      │
│  - file dialogs, entry fields ,buttons                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Create de GUI
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKGROUND THREADS (Daemon)                    │
│                                                             │
│  1. response_thread (porneste in connect())                 │  	                                   
│         - asteapta continuu mesaje de la server             │
│         - detecteaza fragmente si trimite Ack               │
│         - pune raspunsurile in response_queue(thread safe)  │
│                                                             │
│  2. handle_thread (porneste in start_threading())           │
│         - Gets responses from response_queue                │
│         - apeleaza gui_callback() pentru a updata GUI       │
│                                                             │
│  3. send_get_thread (porneste la apasarea butonului GET)    │
│         - apeleaza functia send_get()                       │
│                                                             │
│  4. send_post_thread (porneste la apasarea butonului POST)  │
│         - apeleaza functia send_post()                      │
│         - daca este nevoie se fragmenteaza ianinte de send  │
│  5. send_delete_thread(porneste la apasarea butonului DELETE)│
│         - apeleaza functia send_delete()                    │
│                                                             │
│  6. send_move_thread (porneste la apasarea butonului MOVE)  │
│         - apeleaza functia send_move                        │
└─────────────────────────────────────────────────────────────┘
```













