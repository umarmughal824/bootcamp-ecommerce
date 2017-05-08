import React from 'react';
import { shallow } from 'enzyme';
import { assert } from 'chai';
import _ from 'lodash';

import PaymentHistory from './PaymentHistory';
import { generateFakeKlasses } from '../factories';

describe("PaymentHistory", () => {
  let renderPaymentHistory = (klassesData) => (
    shallow(
      <PaymentHistory
        klasses={{
          data: klassesData
        }}
      />
    )
  );

  let setPaymentValues = (klassesData, paymentAmount) => (
    _.map(klassesData,
      (klass) => (_.set(klass, 'total_paid', paymentAmount))
    )
  );

  it('should show rows of payment history information', () => {
    let klassCount = 3;
    let paymentAmount = 100;
    let fakeKlasses = generateFakeKlasses(klassCount);
    // Set all fake klasses to have payments
    fakeKlasses = setPaymentValues(fakeKlasses, paymentAmount);
    fakeKlasses[0].price = 1000;
    fakeKlasses[1].price = paymentAmount;

    let wrapper = renderPaymentHistory(fakeKlasses);
    let paymentHistoryTableRows = wrapper.find('tbody tr');
    assert.equal(paymentHistoryTableRows.length, klassCount);
    assert.include(paymentHistoryTableRows.at(0).html(), `$${paymentAmount} out of $1,000`);
    assert.include(paymentHistoryTableRows.at(1).html(), `$${paymentAmount}`);
  });

  it('should now show payment history information for klasses with no payments', () => {
    let klassCount = 3;
    let fakeKlasses = generateFakeKlasses(klassCount);
    // Set all fake klasses to have payments
    fakeKlasses = setPaymentValues(fakeKlasses, 100);
    // Set one of the klasses to have no payment
    fakeKlasses[1].total_paid = 0;

    let wrapper = renderPaymentHistory(fakeKlasses);
    let paymentHistoryTableRows = wrapper.find('tbody tr');
    assert.equal(paymentHistoryTableRows.length, klassCount - 1);
  });
});