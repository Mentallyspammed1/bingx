'use strict';

const abstractMethodFactory = require('./abstractMethodFactory');

/**
 * @core/VideoMixin.js
 * @description Mixin that adds video search functionality to a driver module.
 * Drivers using this mixin must implement `getVideoSearchUrl`.
 */
module.exports = function VideoMixin(BaseClass) {
  const WithVideoFeatures = class extends BaseClass {
    /**
     * Indicates if this driver supports video searches.
     * Concrete drivers should override this method to return `true`.
     * @returns {boolean}
     */
    hasVideoSupport() {
      return false; // Default to false; concrete drivers must explicitly set to true.
    }
  };

  // Use the factory to add the abstract method 'getVideoSearchUrl'.
  // This enforces that any class using this mixin must implement the method.
  return abstractMethodFactory(WithVideoFeatures, ['getVideoSearchUrl']);
};
