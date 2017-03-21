const path = require("path");
const webpack = require("webpack");

module.exports = {
  config: {
    entry: {
      'payment': ['babel-polyfill', './static/js/entry/payment'],
      'sentry_client': './static/js/entry/sentry_client.js',
      'style': './static/js/entry/style',
    },
    module: {
      rules: [
        {
          test: /\.(svg|ttf|woff|woff2|eot|gif)$/,
          use: 'url-loader'
        },
        {
          test: /\.scss$/,
          exclude: /node_modules/,
          use: [
            { loader: 'style-loader' },
            { loader: 'css-loader' },
            { loader: 'postcss-loader' },
            { loader: 'sass-loader' },
          ]
        },
        {
          test: /\.css$/,
          exclude: /node_modules/,
          use: [
            { loader: 'style-loader' },
            { loader: 'css-loader' }
          ]
        },
      ]
    },
    resolve: {
      modules: [
        path.join(__dirname, "static/js"),
        "node_modules"
      ],
      extensions: ['.js', '.jsx'],
      alias: {
        react: path.resolve('./node_modules/react')
      }
    },
    performance: {
      hints: false
    }
  },
  babelSharedLoader: {
    test: /\.jsx?$/,
    exclude: /node_modules/,
    loader: 'babel-loader',
    query: {
      "presets": [
        ["env", { "modules": false }],
        "latest",
        "react",
      ],
      "ignore": [
        "node_modules/**"
      ],
      "plugins": [
        "transform-flow-strip-types",
        "react-hot-loader/babel",
        "transform-object-rest-spread",
        "transform-class-properties",
        "syntax-dynamic-import",
      ]
    }
  },
};
