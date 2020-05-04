// @flow
/* global SETTINGS: false */
import React from "react"
import { compose } from "redux"
import { connect } from "react-redux"
import { Link } from "react-router-dom"
import { mutateAsync, connectRequest, requestAsync } from "redux-query"
import { path, pathOr } from "ramda"
import { createStructuredSelector } from "reselect"
import {MetaTags} from "react-meta-tags"

import { addUserNotification } from "../../actions"
import {ALERT_TYPE_TEXT, VIEW_PROFILE_PAGE_TITLE} from "../../constants"
import queries from "../../lib/queries"
import { routes } from "../../lib/urls"
import {formatTitle} from "../../util/util"

import { updateEmailSelector } from "../../lib/queries/auth"
import { qsVerificationCodeSelector } from "../../lib/selectors"

import type { RouterHistory, Location } from "react-router"
import type { updateEmailResponse } from "../../flow/authTypes"
import users from "../../lib/queries/users"
import type { Response } from "redux-query"
import type { User } from "../../flow/authTypes"

type Props = {
  isLoading: boolean,
  addUserNotification: Function,
  location: Location,
  history: RouterHistory,
  updateEmail: ?updateEmailResponse,
  getCurrentUser: () => Promise<Response<User>>
}

export class EmailConfirmPage extends React.Component<Props> {
  async componentDidUpdate(prevProps: Props) {
    const {
      addUserNotification,
      updateEmail,
      history,
      getCurrentUser
    } = this.props
    const prevState = path(["updateEmail", "state"], prevProps)
    if (updateEmail && updateEmail !== prevState && updateEmail.confirmed) {
      addUserNotification({
        "email-verified": {
          type:  ALERT_TYPE_TEXT,
          props: {
            text:
              "Success! We've verified your email. You email has been updated."
          }
        }
      })
      await getCurrentUser()
    } else {
      addUserNotification({
        "email-verified": {
          type:  ALERT_TYPE_TEXT,
          color: "danger",
          props: {
            text: "Error! No confirmation code was provided or it has expired."
          }
        }
      })
    }
    history.push(routes.accountSettings)
  }

  render() {
    const { isLoading, updateEmail } = this.props
    return (
        <div className="container auth-page">
                  <MetaTags>
          <title>{formatTitle(EMAIL_CONFIRM_PAGE_TITLE)}</title>
        </MetaTags>
          <div className="row">
            <div className="col">
              {isLoading && <p>Confirming...</p>}
              {!isLoading && updateEmail && updateEmail.confirmed && (
                <p>Confirmed!</p>
              )}

              {!isLoading &&
                ((updateEmail && !updateEmail.confirmed) || !updateEmail) && (
                <React.Fragment>
                  <p>No confirmation code was provided or it has expired.</p>
                  <Link to={routes.accountSettings}>
                      Click Account Settings
                  </Link>{" "}
                    to change the email again.
                </React.Fragment>
              )}
            </div>
          </div>
        </div>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  updateEmail: updateEmailSelector,
  isLoading:   pathOr(true, ["queries", "updateEmail", "isPending"]),
  params:      createStructuredSelector({
    verificationCode: qsVerificationCodeSelector
  })
})

const getCurrentUser = () =>
  requestAsync({
    ...users.currentUserQuery(),
    force: true
  })

const confirmEmail = (code: string) =>
  mutateAsync(queries.auth.confirmEmailMutation(code))

const mapPropsToConfig = ({ params: { verificationCode } }) =>
  confirmEmail(verificationCode)

const mapDispatchToProps = {
  addUserNotification,
  getCurrentUser
}

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(EmailConfirmPage)
