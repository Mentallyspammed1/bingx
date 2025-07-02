// core/GifMixin.js
'use strict';
const enforceAbstractMethods = require('./abstractMethodFactory');

const gifAbstractMethods = [
  'getGifSearchUrl',    // Expected to return a string (URL). Params: (query, page)
  'parseResults', // Expected to parse data and return an array. Params: (cheerioInstance, rawHtmlOrJsonData, parserOptions)
];

/**
 * GifMixin - A factory function that creates a mixin to add GIF-related abstract method requirements.
 * @param {Function} BaseClass - The base class constructor to extend.
 * @returns {Function} A new class constructor with enforced abstract methods for GIFs.
 */
module.exports = (BaseClass) => {
    // Following the same pattern as VideoMixin and original file content.
    if (typeof enforceAbstractMethods === 'function') {
        return enforceAbstractMethods(BaseClass, gifAbstractMethods);
    }
    class MixedGif extends BaseClass {
        // constructor(...args) {
        //     super(...args);
        //     if (this.constructor === MixedGif) {
        //         if (typeof this.getGifSearchUrl !== 'function') {
        //             throw new Error("Class using GifMixin must implement 'getGifSearchUrl'");
        //         }
        //         // parseResults is shared, but a GIF-specific implementation might be checked for
        //         if (typeof this.parseResults !== 'function') { // Or a more specific gifParser if that was the pattern
        //             throw new Error("Class using GifMixin must implement 'parseResults' (or a specific gifParser)");
        //         }
        //     }
        // }
    }
    return MixedGif;
};
