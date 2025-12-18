'use strict';

const OverwriteError = require('./OverwriteError');

/**
 * AbstractModule base class for all content scrapers.
 * Requires subclasses to override name, firstpage, and URL/parser methods.
 * Supports mixins to add video or gif scraping methods.
 */
class AbstractModule {
  constructor(options = {}) {
    this.query = (typeof options.query === 'string') ? options.query.trim() : '';
    this.options = options || {};
    this.page = this.firstpage;
  }

  get name() {
    throw new OverwriteError('name');
  }

  get firstpage() {
    throw new OverwriteError('firstpage');
  }

  setQuery(newQuery) {
    this.query = (typeof newQuery === 'string') ? newQuery.trim() : '';
  }

  static with(...mixins) {
    return mixins.reduce((c, mixin) => {
      if(typeof mixin === 'function') return mixin(c);
      console.warn('[AbstractModule.with] Invalid mixin:', mixin);
      return c;
    }, this);
  }
}

module.exports = AbstractModule;
