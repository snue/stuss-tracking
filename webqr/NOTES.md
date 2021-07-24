there are three polyfills:
- Promise, TextEncoder, (bundled to avoid connection overhead and to simplify code) (4.4K minified)
- WebCrypto Shim (11K minified)
- WebCrypto Polyfill (forge)

without a proper testing environment (aka every single old chrome, safari, iOS and firefox version), it is time-consuming to figure out when the crypto shim is needed without breaking functionality (see iOS 9 below). therefore we include it when the native api does not support subtlecrypto or fails otherwise. if it fails again, we use the pure js crypto.

modern devices should not need any of the polyfills. but we only had two old phones to test:

- android with chrome 39: actually only needed the hash as an object with a name property, instead of just the string. this could have been solved by the shim, but I figured it out by reviewing its source code (after MDN wasn't too helpful). we didn't try to include it (see above).
- iPhone with iOS 9: window.crypto exists, but window.crypto.subtle doesn't. the WebCrypto shim seems to not support the device ("TypeError: Unsupported JWK algorithm RSA-OAEP-256"). however, forge saves it (with a lot of js overhead, though). and it needs the TextEncoder polyfill. there are organisational time contrains which hinder us from adjusting the available polyfills, or even write out own, so we use what is working.

other caveats:
- forge takes the text as a string, and not as an Uint8Array, as opposed to WebCrypto. when the wrong type is supplied, forge nevertheless converts the array to an overlong string version and produces rubbish without a warning. (TODO: open issue)
