// core/VideoMixin.js
'use strict';
const enforceAbstractMethods = require('./abstractMethodFactory');

const videoAbstractMethods = [
  'getVideoSearchUrl',    // Expected to return a string (URL). Params: (query, page)
  'parseResults', // Expected to parse data and return an array. Params: (cheerioInstance, rawHtmlOrJsonData, parserOptions)
];

/**
 * VideoMixin - A factory function that creates a mixin to add video-related abstract method requirements.
 * @param {Function} BaseClass - The base class constructor to extend.
 * @returns {Function} A new class constructor with enforced abstract methods for videos.
 */
module.exports = (BaseClass) => {
    // The user's latest drivers (e.g. Motherless.js) show:
    // `var Motherless = (function (_AbstractModule$with) { ... }(_AbstractModule2.default.with(_VideoMixin2.default));`
    // This means VideoMixin needs to be a function that takes a class and returns a class.
    // The `enforceAbstractMethods` utility would be a way to achieve this if it's defined.
    // If `enforceAbstractMethods` is not available or not the intended mechanism,
    // this mixin might just be conceptual or the `with` method on AbstractModule handles it differently.
    // For now, assuming `enforceAbstractMethods` is the intended way as per the original file content.
    if (typeof enforceAbstractMethods === 'function') {
        return enforceAbstractMethods(BaseClass, videoAbstractMethods);
    }
    // Fallback: If enforceAbstractMethods is not available, return a modified class
    // that conceptually indicates these methods are expected. This is less robust.
    class MixedVideo extends BaseClass {
        // constructor(...args) {
        //     super(...args);
        //     if (this.constructor === MixedVideo) { // Ensure not called on an abstract class instance
        //         if (typeof this.getVideoSearchUrl !== 'function') {
        //             throw new Error("Class using VideoMixin must implement 'getVideoSearchUrl'");
        //         }
        //         if (typeof this.parseResults !== 'function') {
        //             throw new Error("Class using VideoMixin must implement 'parseResults'");
        //         }
        //     }
        // }
    }
    return MixedVideo;
};
