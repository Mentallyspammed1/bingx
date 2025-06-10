// core/VideoMixin.js
'use strict';
const enforceAbstractMethods = require('./abstractMethodFactory');

const videoAbstractMethods = [
  'videoUrl',    // Expected to return a string (URL). Params: (query, page)
  'videoParser', // Expected to parse data and return an array. Params: (cheerioInstance, rawHtmlOrJsonData)
];

module.exports = (BaseClass) => enforceAbstractMethods(BaseClass, videoAbstractMethods);
