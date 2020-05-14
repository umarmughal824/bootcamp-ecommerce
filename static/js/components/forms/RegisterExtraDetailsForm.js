// @flow
import React from "react"
import { Formik, Form } from "formik"

import { profileValidation } from "../../lib/validation"
import { ProfileFields } from "./ProfileFormFields"

type Props = {
  onSubmit: Function
}

const INITIAL_VALUES = {
  profile: {
    birth_year:        "",
    gender:            "",
    company:           "",
    job_title:         "",
    job_function:      "",
    industry:          "",
    company_size:      "",
    years_experience:  "",
    highest_education: ""
  }
}

const RegisterExtraDetailsForm = ({ onSubmit }: Props) => (
  <Formik
    onSubmit={onSubmit}
    validationSchema={profileValidation}
    initialValues={INITIAL_VALUES}
    render={({ isSubmitting }) => (
      <Form>
        <ProfileFields />
        <div className="row submit-row no-gutters justify-content-end">
          <button
            type="submit"
            className="btn btn-primary btn-light-blue"
            disabled={isSubmitting}
          >
            Continue
          </button>
        </div>
      </Form>
    )}
  />
)

export default RegisterExtraDetailsForm
