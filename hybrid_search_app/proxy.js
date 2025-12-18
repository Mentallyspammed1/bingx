// A simple Node.js HTTP proxy server
const http = require('http')
const url = require('url')

const PORT = 8080

const server = http.createServer((client_req, client_res) => {
    const requestUrl = url.parse(client_req.url)
    const options = {
        hostname: requestUrl.hostname,
        port: requestUrl.port || 80,
        path: requestUrl.path,
        method: client_req.method,
        headers: client_req.headers
    }

    console.log(`[PROXY] Forwarding request to: ${options.hostname}${options.path}`)

    // Create a new request to the target server
    const proxy_req = http.request(options, (proxy_res) => {
        // Send the response from the target server back to the original client
        client_res.writeHead(proxy_res.statusCode, proxy_res.headers)
        proxy_res.pipe(client_res, {
            end: true
        })
    })

    // Handle errors
    proxy_req.on('error', (e) => {
        console.error(`[PROXY] Error: ${e.message}`)
        client_res.writeHead(500)
        client_res.end('Proxy error')
    })

    // Pipe the body of the original request to the new request
    client_req.pipe(proxy_req, {
        end: true
    })
})

server.listen(PORT, () => {
    console.log(`[PROXY] Simple HTTP proxy server running on http://localhost:${PORT}`)
})

server.on('error', (e) => {
    if (e.code === 'EADDRINUSE') {
        console.error(`[PROXY] Error: Port ${PORT} is already in use.`)
    } else {
        console.error(`[PROXY] Server error: ${e.message}`)
    }
})
