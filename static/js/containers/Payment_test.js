/* global SETTINGS: false */
import React from 'react';
import configureTestStore from 'redux-asserts';
import { mount } from 'enzyme';
import { Provider } from 'react-redux';
import { assert } from 'chai';
import sinon from 'sinon';
import _ from 'lodash';

import * as api from '../lib/api';
import {
  setPaymentAmount,
  setSelectedKlassIndex
} from '../actions';
import rootReducer from '../reducers';
import Payment from '../containers/Payment';
import * as util from '../util/util';
import {
  makeRequestActionType,
  makeReceiveSuccessActionType
} from '../rest';

const REQUEST_PAYMENT = makeRequestActionType('payment');
const RECEIVE_PAYMENT_SUCCESS = makeReceiveSuccessActionType('payment');
const REQUEST_KLASSES = makeRequestActionType('klasses');
const RECEIVE_KLASSES_SUCCESS = makeReceiveSuccessActionType('klasses');

const generateFakeKlasses = (numKlasses = 1) => {
  return _.times(numKlasses, (i) => ({
    klass_name: `Bootcamp 1 Klass ${i}`,
    klass_id: i
  }));
};

describe('Payment container', () => {
  let store, listenForActions, sandbox, fetchStub,
    klassesUrl, klassesStub; // eslint-disable-line no-unused-vars

  beforeEach(() => {
    SETTINGS.user = {
      full_name: "john doe",
      username: "johndoe"
    };

    store = configureTestStore(rootReducer);
    listenForActions = store.createListenForActions();
    sandbox = sinon.sandbox.create();
    fetchStub = sandbox.stub(api, 'fetchJSONWithCSRF');
    klassesUrl = `/api/v0/klasses/${SETTINGS.user.username}/`;
  });

  afterEach(() => {
    sandbox.restore();
  });

  let renderPaymentComponent = (props = {}) => (
    mount(
      <Provider store={store}>
        <Payment {...props} />
      </Provider>
    )
  );

  let renderFullPaymentPage = (props = {}) => {
    let wrapper;
    return listenForActions([REQUEST_KLASSES, RECEIVE_KLASSES_SUCCESS], () => {
      wrapper = renderPaymentComponent(props);
    }).then(() => {
      return Promise.resolve(wrapper);
    });
  };

  it('does not have a selected klass by default', () => {
    let fakeKlasses = generateFakeKlasses(3);
    klassesStub = fetchStub.withArgs(klassesUrl)
      .returns(Promise.resolve(fakeKlasses));

    return renderFullPaymentPage().then((wrapper) => {
      assert.isUndefined(wrapper.find('Payment').prop('selectedKlass'));
    });
  });

  it('sets a selected klass', () => {
    let fakeKlasses = generateFakeKlasses(3);
    klassesStub = fetchStub.withArgs(klassesUrl)
      .returns(Promise.resolve(fakeKlasses));
    store.dispatch(setSelectedKlassIndex(2));

    return renderFullPaymentPage().then((wrapper) => {
      assert.deepEqual(wrapper.find('Payment').prop('selectedKlass'), fakeKlasses[2]);
    });
  });

  describe('UI', () => {
    const klassTitleSelector = 'h2.klass-title',
      klassDropdownSelector = 'select.klass-select',
      welcomeMessageSelector = 'h3.intro';

    it('shows the selected klass', () => {
      let fakeKlasses = generateFakeKlasses(3);
      klassesStub = fetchStub.withArgs(klassesUrl)
        .returns(Promise.resolve(fakeKlasses));
      store.dispatch(setSelectedKlassIndex(0));

      return renderFullPaymentPage().then((wrapper) => {
        let title = wrapper.find(klassTitleSelector);
        assert.equal(title.text(), fakeKlasses[0].klass_name);
      });
    });

    it('shows a dropdown if multiple klasses are available', () => {
      [
        [1, false],
        [2, true]
      ].forEach((numKlasses, shouldShowDropdown) => {
        let fakeKlasses = generateFakeKlasses(numKlasses);
        klassesStub = fetchStub.withArgs(klassesUrl)
          .returns(Promise.resolve(fakeKlasses));

        return renderFullPaymentPage().then((wrapper) => {
          assert.equal(wrapper.find(klassDropdownSelector).exists(), shouldShowDropdown);
        });
      });
    });

    it('does not show the name of the user if it is blank', () => {
      SETTINGS.user.full_name = '';
      klassesStub = fetchStub
        .withArgs(klassesUrl)
        .returns(Promise.resolve(generateFakeKlasses(1)));
      return renderFullPaymentPage().then((wrapper) => {
        let welcomeMessage = wrapper.find(welcomeMessageSelector);
        assert.equal(welcomeMessage.text(), "Welcome to MIT Bootcamps");
      });
    });
  });

  describe('payment functionality', () => {
    beforeEach(() => {
      klassesStub = fetchStub
        .withArgs(klassesUrl)
        .returns(Promise.resolve(generateFakeKlasses(1)));
      store.dispatch(setSelectedKlassIndex(0));
    });

    it('sets a price', () => {
      return renderFullPaymentPage().then((wrapper) => {
        wrapper.find('input[id="payment-amount"]').props().onChange({
          target: {
            value: "123"
          }
        });
        assert.equal(store.getState().ui.paymentAmount, "123");
      });
    });

    it('sends a payment when API is contacted', () => {
      store.dispatch(setPaymentAmount("123"));
      fetchStub.withArgs('/api/v0/payment/').returns(Promise.resolve());
      return renderFullPaymentPage().then((wrapper) => {
        return listenForActions([REQUEST_PAYMENT, RECEIVE_PAYMENT_SUCCESS], () => {
          wrapper.find('.payment-button').simulate('click');
        });
      });
    });

    it('constructs a form to be sent to Cybersource and submits it', () => {
      let url = '/x/y/z';
      let payload = {
        'pay': 'load'
      };
      fetchStub.withArgs('/api/v0/payment/').returns(Promise.resolve({
        'url': url,
        'payload': payload
      }));

      let submitStub = sandbox.stub();
      let fakeForm = document.createElement("form");
      fakeForm.setAttribute("class", "fake-form");
      fakeForm.submit = submitStub;
      let createFormStub = sandbox.stub(util, 'createForm').returns(fakeForm);

      return renderFullPaymentPage().then((wrapper) => {
        return listenForActions([REQUEST_PAYMENT, RECEIVE_PAYMENT_SUCCESS], () => {
          wrapper.find('.payment-button').simulate('click');
        }).then(() => {
          return new Promise(resolve => {
            setTimeout(() => {
              assert.equal(createFormStub.callCount, 1);
              assert.deepEqual(createFormStub.args[0], [url, payload]);

              assert(document.body.querySelector(".fake-form"), 'fake form not found in body');
              assert.equal(submitStub.callCount, 1);
              assert.deepEqual(submitStub.args[0], []);

              resolve();
            }, 50);
          });
        });
      });
    });
  });
});
