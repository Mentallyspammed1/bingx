// core/GifMixin.js
'use strict';
const enforceAbstractMethods = require('./abstractMethodFactory');

const gifAbstractMethods = [
  'gifUrl',    // Expected to return a string (URL). Params: (query, page)
  'gifParser', // Expected to parse data and return an array. Params: (cheerioInstance, rawHtmlOrJsonData)
];

module.exports = (BaseClass) => enforceAbstractMethods(BaseClass, gifAbstractMethods);
