import answer
import trio

async def foo(request):
    return answer.Response(b'YAAY!\n')

app = answer.Answer()
app.router.add_route('/foo', foo)
trio.run(app.run)
