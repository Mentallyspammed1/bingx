'use strict';

Object.defineProperty(exports, "__esModule", {
  value: true
});

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
 * @file GifMixin.js
 * A mixin factory that enhances a base class with abstract GIF-related methods.
 * Classes applying this mixin are contractually obligated to implement `getGifSearchUrl()`
 * and rely on `parseResults()` for GIF parsing capabilities.
 */
var GifMixin = function (BaseClass) {
  var GifFeatureMixin = function (_BaseClass) {
    (0, _inherits3.default)(GifFeatureMixin, _BaseClass);

    function GifFeatureMixin() {
      (0, _classCallCheck3.default)(this, GifFeatureMixin);
      return (0, _possibleConstructorReturn3.default)(this, (GifFeatureMixin.__proto__ || (0, _getPrototypeOf2.default)(GifFeatureMixin)).apply(this, arguments));
    }

    (0, _createClass3.default)(GifFeatureMixin, [{
      key: 'getGifSearchUrl',
      /**
       * Abstract method to construct the full URL for a GIF search query.
       * This method MUST be overridden by any concrete driver class that uses this mixin.
       *
       * @param {string} query - The search query term.
       * @param {number} page - The page number for the search results.
       * @returns {string} The fully qualified URL for GIF search.
       * @throws {OverwriteError} If this method is not implemented by the consuming class.
       */
      value: function getGifSearchUrl(query, page) {
        throw new _OverwriteError2.default('getGifSearchUrl');
      }
    }, {
      key: 'hasGifSupport',
      /**
       * Indicates if this driver supports GIF searches.
       * Concrete drivers should override this method to return `true`.
       * @returns {boolean}
       */
      value: function hasGifSupport() {
        return false; // Default to false; concrete drivers must explicitly set to true.
      }
    }]);
    return GifFeatureMixin;
  }(BaseClass);

  return GifFeatureMixin;
};

exports.default = GifMixin;
module.exports = exports['default'];