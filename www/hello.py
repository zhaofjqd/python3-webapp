
def  application(environ,start_reponse):
    start_reponse('200 OK',[('Content-type','text/html')])
    body = '<h1>hello ,%s</h1>' %(environ.items())
    return [body.encode('utf-8')]
