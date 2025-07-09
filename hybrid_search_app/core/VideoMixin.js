'use strict';

var _getPrototypeOf = require('babel-runtime/core-js/object/get-prototype-of');
var _getPrototypeOf2 = _interopRequireDefault(_getPrototypeOf);
var _classCallCheck2 = require('babel-runtime/helpers/classCallCheck');
var _classCallCheck3 = _interopRequireDefault(_classCallCheck2);
var _createClass2 = require('babel-runtime/helpers/createClass');
var _createClass3 = _interopRequireDefault(_createClass2);
var _possibleConstructorReturn2 = require('babel-runtime/helpers/possibleConstructorReturn');
var _possibleConstructorReturn3 = _interopRequireDefault(_possibleConstructorReturn2);
var _inherits2 = require('babel-runtime/helpers/inherits');
var _inherits3 = _interopRequireDefault(_inherits2);

var _OverwriteError = require('./OverwriteError');
var _OverwriteError2 = _interopRequireDefault(_OverwriteError);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * @core/VideoMixin.js
 * @description Mixin that adds video search functionality to a driver module.
 * Drivers using this mixin must implement `getVideoSearchUrl`.
 */
module.exports = function VideoMixin(BaseClass) {
  var WithVideoFeatures = function (_BaseClass) {
    (0, _inherits3.default)(WithVideoFeatures, _BaseClass);

    function WithVideoFeatures() {
      (0, _classCallCheck3.default)(this, WithVideoFeatures);
      return (0, _possibleConstructorReturn3.default)(this, (WithVideoFeatures.__proto__ || (0, _getPrototypeOf2.default)(WithVideoFeatures)).apply(this, arguments));
    }

    (0, _createClass3.default)(WithVideoFeatures, [{
      key: 'getVideoSearchUrl',
      /**
       * Abstract method to construct the full URL for a video search query.
       * This method MUST be overridden by the concrete driver class that uses this mixin.
       *
       * @param {string} query - The search query term.
       * @param {number} page - The page number for the search results.
       * @returns {string} The fully qualified URL for video search.
       * @throws {OverwriteError} If this method is not implemented by the consuming class.
       */
      value: function getVideoSearchUrl(query, page) {
        throw new _OverwriteError2.default('getVideoSearchUrl');
      }
    }, {
      key: 'hasVideoSupport',
      /**
       * Indicates if this driver supports video searches.
       * Concrete drivers should override this method to return `true`.
       * @returns {boolean}
       */
      value: function hasVideoSupport() {
        return false; // Default to false; concrete drivers must explicitly set to true.
      }
    }]);
    return WithVideoFeatures;
  }(BaseClass);

  return WithVideoFeatures;
};