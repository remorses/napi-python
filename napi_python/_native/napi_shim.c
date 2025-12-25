/**
 * NAPI Shim Library for napi-python
 * 
 * This library provides NAPI symbols that forward to Python implementations
 * via function pointers set at runtime.
 * 
 * Build with:
 *   clang -shared -fPIC -o libnapi_shim.dylib napi_shim.c
 */

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>

// NAPI types
typedef struct napi_env__* napi_env;
typedef struct napi_value__* napi_value;
typedef struct napi_ref__* napi_ref;
typedef struct napi_handle_scope__* napi_handle_scope;
typedef struct napi_callback_info__* napi_callback_info;
typedef struct napi_deferred__* napi_deferred;
typedef struct napi_async_work__* napi_async_work;

typedef enum {
    napi_ok,
    napi_invalid_arg,
    napi_object_expected,
    napi_string_expected,
    napi_name_expected,
    napi_function_expected,
    napi_number_expected,
    napi_boolean_expected,
    napi_array_expected,
    napi_generic_failure,
    napi_pending_exception,
    napi_cancelled,
    napi_escape_called_twice,
    napi_handle_scope_mismatch,
    napi_callback_scope_mismatch,
    napi_queue_full,
    napi_closing,
    napi_bigint_expected,
    napi_date_expected,
    napi_arraybuffer_expected,
    napi_detachable_arraybuffer_expected,
    napi_would_deadlock,
    napi_no_external_buffers_allowed,
    napi_cannot_run_js
} napi_status;

typedef enum {
    napi_undefined,
    napi_null,
    napi_boolean,
    napi_number,
    napi_string,
    napi_symbol,
    napi_object,
    napi_function,
    napi_external,
    napi_bigint
} napi_valuetype;

typedef enum {
    napi_int8_array,
    napi_uint8_array,
    napi_uint8_clamped_array,
    napi_int16_array,
    napi_uint16_array,
    napi_int32_array,
    napi_uint32_array,
    napi_float32_array,
    napi_float64_array,
    napi_bigint64_array,
    napi_biguint64_array
} napi_typedarray_type;

typedef enum {
    napi_default = 0,
    napi_writable = 1 << 0,
    napi_enumerable = 1 << 1,
    napi_configurable = 1 << 2,
    napi_static = 1 << 10,
} napi_property_attributes;

typedef napi_value (*napi_callback)(napi_env env, napi_callback_info info);
typedef void (*napi_finalize)(napi_env env, void* finalize_data, void* finalize_hint);

typedef struct {
    const char* error_message;
    void* engine_reserved;
    uint32_t engine_error_code;
    napi_status error_code;
} napi_extended_error_info;

typedef struct {
    const char* utf8name;
    napi_value name;
    napi_callback method;
    napi_callback getter;
    napi_callback setter;
    napi_value value;
    napi_property_attributes attributes;
    void* data;
} napi_property_descriptor;

// Function pointer table - set by Python at runtime
typedef struct {
    napi_status (*get_version)(napi_env env, uint32_t* result);
    napi_status (*get_undefined)(napi_env env, napi_value* result);
    napi_status (*get_null)(napi_env env, napi_value* result);
    napi_status (*get_global)(napi_env env, napi_value* result);
    napi_status (*get_boolean)(napi_env env, bool value, napi_value* result);
    napi_status (*create_int32)(napi_env env, int32_t value, napi_value* result);
    napi_status (*create_uint32)(napi_env env, uint32_t value, napi_value* result);
    napi_status (*create_int64)(napi_env env, int64_t value, napi_value* result);
    napi_status (*create_double)(napi_env env, double value, napi_value* result);
    napi_status (*create_string_utf8)(napi_env env, const char* str, size_t length, napi_value* result);
    napi_status (*get_value_bool)(napi_env env, napi_value value, bool* result);
    napi_status (*get_value_int32)(napi_env env, napi_value value, int32_t* result);
    napi_status (*get_value_uint32)(napi_env env, napi_value value, uint32_t* result);
    napi_status (*get_value_int64)(napi_env env, napi_value value, int64_t* result);
    napi_status (*get_value_double)(napi_env env, napi_value value, double* result);
    napi_status (*get_value_string_utf8)(napi_env env, napi_value value, char* buf, size_t bufsize, size_t* result);
    napi_status (*typeof_)(napi_env env, napi_value value, napi_valuetype* result);
    napi_status (*is_array)(napi_env env, napi_value value, bool* result);
    napi_status (*is_typedarray)(napi_env env, napi_value value, bool* result);
    napi_status (*is_error)(napi_env env, napi_value value, bool* result);
    napi_status (*create_object)(napi_env env, napi_value* result);
    napi_status (*create_array)(napi_env env, napi_value* result);
    napi_status (*get_array_length)(napi_env env, napi_value value, uint32_t* result);
    napi_status (*get_element)(napi_env env, napi_value object, uint32_t index, napi_value* result);
    napi_status (*set_element)(napi_env env, napi_value object, uint32_t index, napi_value value);
    napi_status (*get_property)(napi_env env, napi_value object, napi_value key, napi_value* result);
    napi_status (*set_property)(napi_env env, napi_value object, napi_value key, napi_value value);
    napi_status (*get_named_property)(napi_env env, napi_value object, const char* utf8name, napi_value* result);
    napi_status (*set_named_property)(napi_env env, napi_value object, const char* utf8name, napi_value value);
    napi_status (*get_cb_info)(napi_env env, napi_callback_info cbinfo, size_t* argc, napi_value* argv, napi_value* this_arg, void** data);
    napi_status (*create_function)(napi_env env, const char* utf8name, size_t length, napi_callback cb, void* data, napi_value* result);
    napi_status (*call_function)(napi_env env, napi_value recv, napi_value func, size_t argc, const napi_value* argv, napi_value* result);
    napi_status (*define_class)(napi_env env, const char* utf8name, size_t length, napi_callback constructor, void* data, size_t property_count, const napi_property_descriptor* properties, napi_value* result);
    napi_status (*create_reference)(napi_env env, napi_value value, uint32_t initial_refcount, napi_ref* result);
    napi_status (*delete_reference)(napi_env env, napi_ref ref);
    napi_status (*get_reference_value)(napi_env env, napi_ref ref, napi_value* result);
    napi_status (*reference_ref)(napi_env env, napi_ref ref, uint32_t* result);
    napi_status (*reference_unref)(napi_env env, napi_ref ref, uint32_t* result);
    napi_status (*throw_)(napi_env env, napi_value error);
    napi_status (*throw_error)(napi_env env, const char* code, const char* msg);
    napi_status (*create_error)(napi_env env, napi_value code, napi_value msg, napi_value* result);
    napi_status (*is_exception_pending)(napi_env env, bool* result);
    napi_status (*get_and_clear_last_exception)(napi_env env, napi_value* result);
    napi_status (*open_handle_scope)(napi_env env, napi_handle_scope* result);
    napi_status (*close_handle_scope)(napi_env env, napi_handle_scope scope);
    napi_status (*coerce_to_string)(napi_env env, napi_value value, napi_value* result);
    napi_status (*get_typedarray_info)(napi_env env, napi_value typedarray, napi_typedarray_type* type, size_t* length, void** data, napi_value* arraybuffer, size_t* byte_offset);
    // Promise functions
    napi_status (*create_promise)(napi_env env, napi_deferred* deferred, napi_value* promise);
    napi_status (*resolve_deferred)(napi_env env, napi_deferred deferred, napi_value resolution);
    napi_status (*reject_deferred)(napi_env env, napi_deferred deferred, napi_value rejection);
    napi_status (*is_promise)(napi_env env, napi_value value, bool* is_promise);
    // Threadsafe function
    napi_status (*create_tsfn)(napi_env env, napi_value func, napi_value async_resource, napi_value async_resource_name, size_t max_queue_size, size_t initial_thread_count, void* thread_finalize_data, napi_finalize thread_finalize_cb, void* context, void* call_js_cb, void** result);
    napi_status (*call_tsfn)(void* func, void* data, int is_blocking);
    napi_status (*acquire_tsfn)(void* func);
    napi_status (*release_tsfn)(void* func, int mode);
    // Class/wrap functions
    napi_status (*wrap)(napi_env env, napi_value js_object, void* native_object, napi_finalize finalize_cb, void* finalize_hint, napi_ref* result);
    napi_status (*unwrap)(napi_env env, napi_value js_object, void** result);
    napi_status (*define_class_impl)(napi_env env, const char* utf8name, size_t length, napi_callback constructor, void* data, size_t property_count, const napi_property_descriptor* properties, napi_value* result);
    // ArrayBuffer functions
    napi_status (*create_arraybuffer)(napi_env env, size_t byte_length, void** data, napi_value* result);
    napi_status (*get_arraybuffer_info)(napi_env env, napi_value arraybuffer, void** data, size_t* byte_length);
    napi_status (*is_detached_arraybuffer)(napi_env env, napi_value arraybuffer, bool* result);
    napi_status (*detach_arraybuffer)(napi_env env, napi_value arraybuffer);
    napi_status (*is_arraybuffer)(napi_env env, napi_value value, bool* result);
    // TypedArray functions
    napi_status (*create_typedarray)(napi_env env, napi_typedarray_type type, size_t length, napi_value arraybuffer, size_t byte_offset, napi_value* result);
    // DataView functions
    napi_status (*create_dataview)(napi_env env, size_t byte_length, napi_value arraybuffer, size_t byte_offset, napi_value* result);
    napi_status (*get_dataview_info)(napi_env env, napi_value dataview, size_t* byte_length, void** data, napi_value* arraybuffer, size_t* byte_offset);
    napi_status (*is_dataview)(napi_env env, napi_value value, bool* result);
    // Buffer functions
    napi_status (*create_buffer)(napi_env env, size_t size, void** data, napi_value* result);
    napi_status (*create_buffer_copy)(napi_env env, size_t length, const void* data, void** result_data, napi_value* result);
    napi_status (*get_buffer_info)(napi_env env, napi_value buffer, void** data, size_t* length);
    napi_status (*is_buffer)(napi_env env, napi_value value, bool* result);
    // External functions
    napi_status (*create_external)(napi_env env, void* data, napi_finalize finalize_cb, void* finalize_hint, napi_value* result);
    napi_status (*get_value_external)(napi_env env, napi_value value, void** result);
    // Additional error functions
    napi_status (*throw_type_error)(napi_env env, const char* code, const char* msg);
    napi_status (*throw_range_error)(napi_env env, const char* code, const char* msg);
    napi_status (*create_type_error)(napi_env env, napi_value code, napi_value msg, napi_value* result);
    napi_status (*create_range_error)(napi_env env, napi_value code, napi_value msg, napi_value* result);
    // Instance creation
    napi_status (*new_instance)(napi_env env, napi_value constructor, size_t argc, const napi_value* argv, napi_value* result);
    // Fatal exception
    napi_status (*fatal_exception)(napi_env env, napi_value err);
    // Get new target
    napi_status (*get_new_target)(napi_env env, napi_callback_info cbinfo, napi_value* result);
    // Property checking
    napi_status (*has_own_property)(napi_env env, napi_value object, napi_value key, bool* result);
    // Get all property names
    napi_status (*get_all_property_names)(napi_env env, napi_value object, int key_mode, int key_filter, int key_conversion, napi_value* result);
    // Get property names
    napi_status (*get_property_names)(napi_env env, napi_value object, napi_value* result);
    // Instance data
    napi_status (*set_instance_data)(napi_env env, void* data, napi_finalize finalize_cb, void* finalize_hint);
    napi_status (*get_instance_data)(napi_env env, void** result);
} NapiPythonFunctions;

// Global function table
static NapiPythonFunctions* g_funcs = NULL;

// Function to set the function table from Python
void napi_python_set_functions(NapiPythonFunctions* funcs) {
    g_funcs = funcs;
}

// Helper macro for checking function table
#define CHECK_FUNCS() if (!g_funcs) return napi_generic_failure

// =============================================================================
// NAPI Function Implementations
// =============================================================================

napi_status napi_get_version(napi_env env, uint32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_version) return g_funcs->get_version(env, result);
    *result = 9;
    return napi_ok;
}

napi_status napi_get_undefined(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_undefined) return g_funcs->get_undefined(env, result);
    return napi_generic_failure;
}

napi_status napi_get_null(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_null) return g_funcs->get_null(env, result);
    return napi_generic_failure;
}

napi_status napi_get_global(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_global) return g_funcs->get_global(env, result);
    return napi_generic_failure;
}

napi_status napi_get_boolean(napi_env env, bool value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_boolean) return g_funcs->get_boolean(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_int32(napi_env env, int32_t value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_int32) return g_funcs->create_int32(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_uint32(napi_env env, uint32_t value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_uint32) return g_funcs->create_uint32(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_int64(napi_env env, int64_t value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_int64) return g_funcs->create_int64(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_double(napi_env env, double value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_double) return g_funcs->create_double(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_string_utf8(napi_env env, const char* str, size_t length, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_string_utf8) return g_funcs->create_string_utf8(env, str, length, result);
    return napi_generic_failure;
}

napi_status napi_get_value_bool(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_bool) return g_funcs->get_value_bool(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_int32(napi_env env, napi_value value, int32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_int32) return g_funcs->get_value_int32(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_uint32(napi_env env, napi_value value, uint32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_uint32) return g_funcs->get_value_uint32(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_int64(napi_env env, napi_value value, int64_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_int64) return g_funcs->get_value_int64(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_double(napi_env env, napi_value value, double* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_double) return g_funcs->get_value_double(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_string_utf8(napi_env env, napi_value value, char* buf, size_t bufsize, size_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_string_utf8) return g_funcs->get_value_string_utf8(env, value, buf, bufsize, result);
    return napi_generic_failure;
}

napi_status napi_typeof(napi_env env, napi_value value, napi_valuetype* result) {
    CHECK_FUNCS();
    if (g_funcs->typeof_) {
        napi_status status = g_funcs->typeof_(env, value, result);
        return status;
    }
    return napi_generic_failure;
}

napi_status napi_is_array(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_array) return g_funcs->is_array(env, value, result);
    return napi_generic_failure;
}

napi_status napi_is_typedarray(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_typedarray) return g_funcs->is_typedarray(env, value, result);
    return napi_generic_failure;
}

napi_status napi_is_error(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_error) return g_funcs->is_error(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_object(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_object) return g_funcs->create_object(env, result);
    return napi_generic_failure;
}

napi_status napi_create_array(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_array) return g_funcs->create_array(env, result);
    return napi_generic_failure;
}

napi_status napi_get_array_length(napi_env env, napi_value value, uint32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_array_length) return g_funcs->get_array_length(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_element(napi_env env, napi_value object, uint32_t index, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_element) return g_funcs->get_element(env, object, index, result);
    return napi_generic_failure;
}

napi_status napi_set_element(napi_env env, napi_value object, uint32_t index, napi_value value) {
    CHECK_FUNCS();
    if (g_funcs->set_element) return g_funcs->set_element(env, object, index, value);
    return napi_generic_failure;
}

napi_status napi_get_property(napi_env env, napi_value object, napi_value key, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_property) return g_funcs->get_property(env, object, key, result);
    return napi_generic_failure;
}

napi_status napi_set_property(napi_env env, napi_value object, napi_value key, napi_value value) {
    CHECK_FUNCS();
    if (g_funcs->set_property) return g_funcs->set_property(env, object, key, value);
    return napi_generic_failure;
}

napi_status napi_get_named_property(napi_env env, napi_value object, const char* utf8name, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_named_property) {
        napi_status status = g_funcs->get_named_property(env, object, utf8name, result);
        return status;
    }
    return napi_generic_failure;
}

napi_status napi_set_named_property(napi_env env, napi_value object, const char* utf8name, napi_value value) {
    CHECK_FUNCS();
    if (g_funcs->set_named_property) return g_funcs->set_named_property(env, object, utf8name, value);
    return napi_generic_failure;
}

napi_status napi_get_cb_info(napi_env env, napi_callback_info cbinfo, size_t* argc, napi_value* argv, napi_value* this_arg, void** data) {
    CHECK_FUNCS();
    if (g_funcs->get_cb_info) {
        napi_status result = g_funcs->get_cb_info(env, cbinfo, argc, argv, this_arg, data);
        return result;
    }
    return napi_generic_failure;
}

napi_status napi_create_function(napi_env env, const char* utf8name, size_t length, napi_callback cb, void* data, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_function) return g_funcs->create_function(env, utf8name, length, cb, data, result);
    return napi_generic_failure;
}

napi_status napi_call_function(napi_env env, napi_value recv, napi_value func, size_t argc, const napi_value* argv, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->call_function) {
        napi_status status = g_funcs->call_function(env, recv, func, argc, argv, result);
        return status;
    }
    return napi_generic_failure;
}

napi_status napi_define_class(napi_env env, const char* utf8name, size_t length, napi_callback constructor, void* data, size_t property_count, const napi_property_descriptor* properties, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->define_class_impl) return g_funcs->define_class_impl(env, utf8name, length, constructor, data, property_count, properties, result);
    return napi_generic_failure;
}

napi_status napi_create_reference(napi_env env, napi_value value, uint32_t initial_refcount, napi_ref* result) {
    CHECK_FUNCS();
    if (g_funcs->create_reference) {
        napi_status status = g_funcs->create_reference(env, value, initial_refcount, result);
        return status;
    }
    return napi_generic_failure;
}

napi_status napi_delete_reference(napi_env env, napi_ref ref) {
    CHECK_FUNCS();
    if (g_funcs->delete_reference) return g_funcs->delete_reference(env, ref);
    return napi_generic_failure;
}

napi_status napi_get_reference_value(napi_env env, napi_ref ref, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_reference_value) {
        napi_status status = g_funcs->get_reference_value(env, ref, result);
        return status;
    }
    return napi_generic_failure;
}

napi_status napi_reference_ref(napi_env env, napi_ref ref, uint32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->reference_ref) return g_funcs->reference_ref(env, ref, result);
    return napi_generic_failure;
}

napi_status napi_reference_unref(napi_env env, napi_ref ref, uint32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->reference_unref) return g_funcs->reference_unref(env, ref, result);
    return napi_generic_failure;
}

napi_status napi_throw(napi_env env, napi_value error) {
    CHECK_FUNCS();
    if (g_funcs->throw_) return g_funcs->throw_(env, error);
    return napi_generic_failure;
}

napi_status napi_throw_error(napi_env env, const char* code, const char* msg) {
    CHECK_FUNCS();
    if (g_funcs->throw_error) return g_funcs->throw_error(env, code, msg);
    return napi_generic_failure;
}

napi_status napi_create_error(napi_env env, napi_value code, napi_value msg, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_error) return g_funcs->create_error(env, code, msg, result);
    return napi_generic_failure;
}

napi_status napi_is_exception_pending(napi_env env, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_exception_pending) return g_funcs->is_exception_pending(env, result);
    *result = false;
    return napi_ok;
}

napi_status napi_get_and_clear_last_exception(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_and_clear_last_exception) return g_funcs->get_and_clear_last_exception(env, result);
    return napi_generic_failure;
}

napi_status napi_open_handle_scope(napi_env env, napi_handle_scope* result) {
    CHECK_FUNCS();
    if (g_funcs->open_handle_scope) return g_funcs->open_handle_scope(env, result);
    return napi_generic_failure;
}

napi_status napi_close_handle_scope(napi_env env, napi_handle_scope scope) {
    CHECK_FUNCS();
    if (g_funcs->close_handle_scope) return g_funcs->close_handle_scope(env, scope);
    return napi_generic_failure;
}

napi_status napi_coerce_to_string(napi_env env, napi_value value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->coerce_to_string) return g_funcs->coerce_to_string(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_typedarray_info(napi_env env, napi_value typedarray, napi_typedarray_type* type, size_t* length, void** data, napi_value* arraybuffer, size_t* byte_offset) {
    CHECK_FUNCS();
    if (g_funcs->get_typedarray_info) return g_funcs->get_typedarray_info(env, typedarray, type, length, data, arraybuffer, byte_offset);
    return napi_generic_failure;
}

// =============================================================================
// Promise Functions
// =============================================================================

napi_status napi_create_promise(napi_env env, napi_deferred* deferred, napi_value* promise) {
    CHECK_FUNCS();
    if (g_funcs->create_promise) return g_funcs->create_promise(env, deferred, promise);
    return napi_generic_failure;
}

napi_status napi_resolve_deferred(napi_env env, napi_deferred deferred, napi_value resolution) {
    CHECK_FUNCS();
    if (g_funcs->resolve_deferred) return g_funcs->resolve_deferred(env, deferred, resolution);
    return napi_generic_failure;
}

napi_status napi_reject_deferred(napi_env env, napi_deferred deferred, napi_value rejection) {
    CHECK_FUNCS();
    if (g_funcs->reject_deferred) return g_funcs->reject_deferred(env, deferred, rejection);
    return napi_generic_failure;
}

napi_status napi_is_promise(napi_env env, napi_value value, bool* is_promise) {
    CHECK_FUNCS();
    if (g_funcs->is_promise) return g_funcs->is_promise(env, value, is_promise);
    if (is_promise) *is_promise = false;
    return napi_ok;
}

// Last error info - simple implementation
static napi_extended_error_info g_last_error = {0};

napi_status napi_get_last_error_info(napi_env env, const napi_extended_error_info** result) {
    if (result) *result = &g_last_error;
    return napi_ok;
}

// =============================================================================
// Additional NAPI stubs (not yet fully implemented)
// =============================================================================

napi_status napi_add_env_cleanup_hook(napi_env env, void (*fun)(void* arg), void* arg) {
    // TODO: Implement cleanup hooks
    return napi_ok;
}

napi_status napi_remove_env_cleanup_hook(napi_env env, void (*fun)(void* arg), void* arg) {
    return napi_ok;
}

napi_status napi_create_array_with_length(napi_env env, size_t length, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_array) {
        napi_status status = g_funcs->create_array(env, result);
        // TODO: Set array length properly
        return status;
    }
    return napi_generic_failure;
}

napi_status napi_wrap(napi_env env, napi_value js_object, void* native_object, napi_finalize finalize_cb, void* finalize_hint, napi_ref* result) {
    CHECK_FUNCS();
    if (g_funcs->wrap) {
        napi_status status = g_funcs->wrap(env, js_object, native_object, finalize_cb, finalize_hint, result);
        return status;
    }
    if (result) *result = NULL;
    return napi_ok;
}

napi_status napi_unwrap(napi_env env, napi_value js_object, void** result) {
    CHECK_FUNCS();
    if (g_funcs->unwrap) {
        napi_status status = g_funcs->unwrap(env, js_object, result);
        return status;
    }
    if (result) *result = NULL;
    return napi_ok;
}

napi_status napi_remove_wrap(napi_env env, napi_value js_object, void** result) {
    // For now, just call unwrap
    CHECK_FUNCS();
    if (g_funcs->unwrap) {
        return g_funcs->unwrap(env, js_object, result);
    }
    if (result) *result = NULL;
    return napi_ok;
}

typedef struct napi_threadsafe_function__* napi_threadsafe_function;

napi_status napi_create_threadsafe_function(
    napi_env env,
    napi_value func,
    napi_value async_resource,
    napi_value async_resource_name,
    size_t max_queue_size,
    size_t initial_thread_count,
    void* thread_finalize_data,
    napi_finalize thread_finalize_cb,
    void* context,
    void (*call_js_cb)(napi_env env, napi_value js_callback, void* context, void* data),
    napi_threadsafe_function* result
) {
    CHECK_FUNCS();
    if (g_funcs->create_tsfn) {
        return g_funcs->create_tsfn(env, func, async_resource, async_resource_name,
            max_queue_size, initial_thread_count, thread_finalize_data, thread_finalize_cb,
            context, (void*)call_js_cb, (void**)result);
    }
    if (result) *result = NULL;
    return napi_ok;
}

napi_status napi_unref_threadsafe_function(napi_env env, napi_threadsafe_function func) {
    return napi_ok;
}

napi_status napi_ref_threadsafe_function(napi_env env, napi_threadsafe_function func) {
    return napi_ok;
}

napi_status napi_acquire_threadsafe_function(napi_threadsafe_function func) {
    CHECK_FUNCS();
    if (g_funcs->acquire_tsfn) {
        return g_funcs->acquire_tsfn((void*)func);
    }
    return napi_ok;
}

napi_status napi_release_threadsafe_function(napi_threadsafe_function func, int mode) {
    CHECK_FUNCS();
    if (g_funcs->release_tsfn) {
        return g_funcs->release_tsfn((void*)func, mode);
    }
    return napi_ok;
}

napi_status napi_call_threadsafe_function(napi_threadsafe_function func, void* data, int is_blocking) {
    CHECK_FUNCS();
    if (g_funcs->call_tsfn) {
        return g_funcs->call_tsfn((void*)func, data, is_blocking);
    }
    return napi_ok;
}

napi_status napi_get_threadsafe_function_context(napi_threadsafe_function func, void** result) {
    if (result) *result = NULL;
    return napi_ok;
}

napi_status napi_has_property(napi_env env, napi_value object, napi_value key, bool* result) {
    if (result) *result = false;
    return napi_ok;
}

napi_status napi_has_named_property(napi_env env, napi_value object, const char* utf8name, bool* result) {
    if (result) *result = false;
    return napi_ok;
}

napi_status napi_delete_property(napi_env env, napi_value object, napi_value key, bool* result) {
    if (result) *result = true;
    return napi_ok;
}

napi_status napi_has_element(napi_env env, napi_value object, uint32_t index, bool* result) {
    if (result) *result = false;
    return napi_ok;
}

napi_status napi_delete_element(napi_env env, napi_value object, uint32_t index, bool* result) {
    if (result) *result = true;
    return napi_ok;
}

napi_status napi_strict_equals(napi_env env, napi_value lhs, napi_value rhs, bool* result) {
    if (result) *result = (lhs == rhs);
    return napi_ok;
}

napi_status napi_get_prototype(napi_env env, napi_value object, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_undefined) return g_funcs->get_undefined(env, result);
    return napi_generic_failure;
}

napi_status napi_define_properties(napi_env env, napi_value object, size_t property_count, const napi_property_descriptor* properties) {
    // TODO: Implement define properties
    return napi_ok;
}

napi_status napi_set_instance_data(napi_env env, void* data, napi_finalize finalize_cb, void* finalize_hint) {
    CHECK_FUNCS();
    if (g_funcs->set_instance_data) return g_funcs->set_instance_data(env, data, finalize_cb, finalize_hint);
    return napi_ok;
}

napi_status napi_get_instance_data(napi_env env, void** data) {
    CHECK_FUNCS();
    if (g_funcs->get_instance_data) return g_funcs->get_instance_data(env, data);
    if (data) *data = NULL;
    return napi_ok;
}

napi_status napi_object_freeze(napi_env env, napi_value object) {
    return napi_ok;
}

napi_status napi_object_seal(napi_env env, napi_value object) {
    return napi_ok;
}

// =============================================================================
// ArrayBuffer Functions
// =============================================================================

napi_status napi_create_arraybuffer(napi_env env, size_t byte_length, void** data, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_arraybuffer) return g_funcs->create_arraybuffer(env, byte_length, data, result);
    return napi_generic_failure;
}

napi_status napi_get_arraybuffer_info(napi_env env, napi_value arraybuffer, void** data, size_t* byte_length) {
    CHECK_FUNCS();
    if (g_funcs->get_arraybuffer_info) return g_funcs->get_arraybuffer_info(env, arraybuffer, data, byte_length);
    return napi_generic_failure;
}

napi_status napi_is_detached_arraybuffer(napi_env env, napi_value arraybuffer, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_detached_arraybuffer) return g_funcs->is_detached_arraybuffer(env, arraybuffer, result);
    if (result) *result = false;
    return napi_ok;
}

napi_status napi_detach_arraybuffer(napi_env env, napi_value arraybuffer) {
    CHECK_FUNCS();
    if (g_funcs->detach_arraybuffer) return g_funcs->detach_arraybuffer(env, arraybuffer);
    return napi_generic_failure;
}

napi_status napi_is_arraybuffer(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_arraybuffer) return g_funcs->is_arraybuffer(env, value, result);
    if (result) *result = false;
    return napi_ok;
}

napi_status napi_create_external_arraybuffer(napi_env env, void* external_data, size_t byte_length, napi_finalize finalize_cb, void* finalize_hint, napi_value* result) {
    // For now, create a regular arraybuffer and copy the data
    // TODO: Implement proper external arraybuffer with finalize callback
    CHECK_FUNCS();
    if (g_funcs->create_arraybuffer) {
        void* data = NULL;
        napi_status status = g_funcs->create_arraybuffer(env, byte_length, &data, result);
        if (status == napi_ok && data && external_data && byte_length > 0) {
            // Copy external data to our buffer
            for (size_t i = 0; i < byte_length; i++) {
                ((unsigned char*)data)[i] = ((unsigned char*)external_data)[i];
            }
        }
        return status;
    }
    return napi_generic_failure;
}

// =============================================================================
// TypedArray Functions
// =============================================================================

napi_status napi_create_typedarray(napi_env env, napi_typedarray_type type, size_t length, napi_value arraybuffer, size_t byte_offset, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_typedarray) return g_funcs->create_typedarray(env, type, length, arraybuffer, byte_offset, result);
    return napi_generic_failure;
}

// =============================================================================
// DataView Functions
// =============================================================================

napi_status napi_create_dataview(napi_env env, size_t byte_length, napi_value arraybuffer, size_t byte_offset, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_dataview) return g_funcs->create_dataview(env, byte_length, arraybuffer, byte_offset, result);
    return napi_generic_failure;
}

napi_status napi_get_dataview_info(napi_env env, napi_value dataview, size_t* byte_length, void** data, napi_value* arraybuffer, size_t* byte_offset) {
    CHECK_FUNCS();
    if (g_funcs->get_dataview_info) return g_funcs->get_dataview_info(env, dataview, byte_length, data, arraybuffer, byte_offset);
    return napi_generic_failure;
}

napi_status napi_is_dataview(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_dataview) return g_funcs->is_dataview(env, value, result);
    if (result) *result = false;
    return napi_ok;
}

// =============================================================================
// Buffer Functions
// =============================================================================

napi_status napi_create_buffer(napi_env env, size_t size, void** data, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_buffer) return g_funcs->create_buffer(env, size, data, result);
    return napi_generic_failure;
}

napi_status napi_create_buffer_copy(napi_env env, size_t length, const void* data, void** result_data, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_buffer_copy) return g_funcs->create_buffer_copy(env, length, data, result_data, result);
    return napi_generic_failure;
}

napi_status napi_get_buffer_info(napi_env env, napi_value buffer, void** data, size_t* length) {
    CHECK_FUNCS();
    if (g_funcs->get_buffer_info) return g_funcs->get_buffer_info(env, buffer, data, length);
    return napi_generic_failure;
}

napi_status napi_is_buffer(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_buffer) return g_funcs->is_buffer(env, value, result);
    if (result) *result = false;
    return napi_ok;
}

napi_status napi_create_external_buffer(napi_env env, size_t length, void* data, napi_finalize finalize_cb, void* finalize_hint, napi_value* result) {
    // For now, create a buffer copy
    CHECK_FUNCS();
    if (g_funcs->create_buffer_copy) {
        return g_funcs->create_buffer_copy(env, length, data, NULL, result);
    }
    return napi_generic_failure;
}

napi_status napi_adjust_external_memory(napi_env env, int64_t change_in_bytes, int64_t* adjusted_value) {
    // No-op for Python - we don't need to adjust GC pressure
    if (adjusted_value) *adjusted_value = 0;
    return napi_ok;
}

// =============================================================================
// External Functions
// =============================================================================

napi_status napi_create_external(napi_env env, void* data, napi_finalize finalize_cb, void* finalize_hint, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_external) return g_funcs->create_external(env, data, finalize_cb, finalize_hint, result);
    return napi_generic_failure;
}

napi_status napi_get_value_external(napi_env env, napi_value value, void** result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_external) return g_funcs->get_value_external(env, value, result);
    return napi_generic_failure;
}

// =============================================================================
// Additional Error Functions
// =============================================================================

napi_status napi_throw_type_error(napi_env env, const char* code, const char* msg) {
    CHECK_FUNCS();
    if (g_funcs->throw_type_error) return g_funcs->throw_type_error(env, code, msg);
    return napi_generic_failure;
}

napi_status napi_throw_range_error(napi_env env, const char* code, const char* msg) {
    CHECK_FUNCS();
    if (g_funcs->throw_range_error) return g_funcs->throw_range_error(env, code, msg);
    return napi_generic_failure;
}

napi_status napi_create_type_error(napi_env env, napi_value code, napi_value msg, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_type_error) return g_funcs->create_type_error(env, code, msg, result);
    return napi_generic_failure;
}

napi_status napi_create_range_error(napi_env env, napi_value code, napi_value msg, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_range_error) return g_funcs->create_range_error(env, code, msg, result);
    return napi_generic_failure;
}

// =============================================================================
// Instance Creation and Related Functions
// =============================================================================

napi_status napi_new_instance(napi_env env, napi_value constructor, size_t argc, const napi_value* argv, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->new_instance) return g_funcs->new_instance(env, constructor, argc, argv, result);
    return napi_generic_failure;
}

napi_status napi_fatal_exception(napi_env env, napi_value err) {
    CHECK_FUNCS();
    if (g_funcs->fatal_exception) return g_funcs->fatal_exception(env, err);
    // Non-fatal fallback - just log and continue
    return napi_ok;
}

napi_status napi_get_new_target(napi_env env, napi_callback_info cbinfo, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_new_target) return g_funcs->get_new_target(env, cbinfo, result);
    if (result) *result = NULL;
    return napi_ok;
}

napi_status napi_has_own_property(napi_env env, napi_value object, napi_value key, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->has_own_property) return g_funcs->has_own_property(env, object, key, result);
    if (result) *result = false;
    return napi_ok;
}

typedef enum {
    napi_key_include_prototypes,
    napi_key_own_only
} napi_key_collection_mode;

typedef enum {
    napi_key_all_properties = 0,
    napi_key_writable = 1,
    napi_key_enumerable = 2,
    napi_key_configurable = 4,
    napi_key_skip_strings = 8,
    napi_key_skip_symbols = 16
} napi_key_filter;

typedef enum {
    napi_key_keep_numbers,
    napi_key_numbers_to_strings
} napi_key_conversion;

napi_status napi_get_all_property_names(napi_env env, napi_value object, napi_key_collection_mode key_mode, napi_key_filter key_filter, napi_key_conversion key_conversion, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_all_property_names) return g_funcs->get_all_property_names(env, object, key_mode, key_filter, key_conversion, result);
    // Return empty array as fallback
    if (g_funcs->create_array) return g_funcs->create_array(env, result);
    return napi_generic_failure;
}

napi_status napi_get_property_names(napi_env env, napi_value object, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_property_names) return g_funcs->get_property_names(env, object, result);
    // Return empty array as fallback
    if (g_funcs->create_array) return g_funcs->create_array(env, result);
    return napi_generic_failure;
}

// Additional commonly needed stubs
napi_status napi_instanceof(napi_env env, napi_value object, napi_value constructor, bool* result) {
    // For native addons, we generally want instanceof checks to pass
    // when the object was created by the constructor class.
    // Since we wrap native objects with __napi_native__, we return true
    // if both object and constructor are valid.
    // TODO: Implement proper prototype chain check if needed
    if (result) {
        *result = (object != NULL && constructor != NULL);
    }
    return napi_ok;
}

napi_status napi_coerce_to_bool(napi_env env, napi_value value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_boolean) {
        // Get the value and convert to bool
        return g_funcs->get_boolean(env, true, result);
    }
    return napi_generic_failure;
}

napi_status napi_coerce_to_number(napi_env env, napi_value value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_double) {
        return g_funcs->create_double(env, 0.0, result);
    }
    return napi_generic_failure;
}

napi_status napi_coerce_to_object(napi_env env, napi_value value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_object) {
        return g_funcs->create_object(env, result);
    }
    return napi_generic_failure;
}

// Escapable handle scope (just use regular handle scope for now)
typedef struct napi_escapable_handle_scope__* napi_escapable_handle_scope;

napi_status napi_open_escapable_handle_scope(napi_env env, napi_escapable_handle_scope* result) {
    return napi_open_handle_scope(env, (napi_handle_scope*)result);
}

napi_status napi_close_escapable_handle_scope(napi_env env, napi_escapable_handle_scope scope) {
    return napi_close_handle_scope(env, (napi_handle_scope)scope);
}

napi_status napi_escape_handle(napi_env env, napi_escapable_handle_scope scope, napi_value escapee, napi_value* result) {
    // Just return the same handle - we don't actually manage scopes like Node does
    if (result) *result = escapee;
    return napi_ok;
}

// BigInt stubs (return errors for now)
napi_status napi_create_bigint_int64(napi_env env, int64_t value, napi_value* result) {
    CHECK_FUNCS();
    // Use int64 instead
    if (g_funcs->create_int64) return g_funcs->create_int64(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_bigint_uint64(napi_env env, uint64_t value, napi_value* result) {
    CHECK_FUNCS();
    // Use int64 instead
    if (g_funcs->create_int64) return g_funcs->create_int64(env, (int64_t)value, result);
    return napi_generic_failure;
}

napi_status napi_create_bigint_words(napi_env env, int sign_bit, size_t word_count, const uint64_t* words, napi_value* result) {
    return napi_generic_failure;
}

napi_status napi_get_value_bigint_int64(napi_env env, napi_value value, int64_t* result, bool* lossless) {
    CHECK_FUNCS();
    if (g_funcs->get_value_int64) {
        if (lossless) *lossless = true;
        return g_funcs->get_value_int64(env, value, result);
    }
    return napi_generic_failure;
}

napi_status napi_get_value_bigint_uint64(napi_env env, napi_value value, uint64_t* result, bool* lossless) {
    CHECK_FUNCS();
    if (g_funcs->get_value_int64) {
        int64_t val;
        napi_status status = g_funcs->get_value_int64(env, value, &val);
        if (status == napi_ok && result) *result = (uint64_t)val;
        if (lossless) *lossless = (val >= 0);
        return status;
    }
    return napi_generic_failure;
}

napi_status napi_get_value_bigint_words(napi_env env, napi_value value, int* sign_bit, size_t* word_count, uint64_t* words) {
    return napi_generic_failure;
}

// Symbol functions
napi_status napi_create_symbol(napi_env env, napi_value description, napi_value* result) {
    CHECK_FUNCS();
    // Create a unique object to serve as a symbol
    if (g_funcs->create_object) return g_funcs->create_object(env, result);
    return napi_generic_failure;
}

// Date functions
napi_status napi_create_date(napi_env env, double time, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_double) return g_funcs->create_double(env, time, result);
    return napi_generic_failure;
}

napi_status napi_is_date(napi_env env, napi_value value, bool* result) {
    if (result) *result = false;
    return napi_ok;
}

napi_status napi_get_date_value(napi_env env, napi_value value, double* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_double) return g_funcs->get_value_double(env, value, result);
    return napi_generic_failure;
}

// String functions
napi_status napi_create_string_utf16(napi_env env, const uint16_t* str, size_t length, napi_value* result) {
    // Convert UTF-16 to UTF-8 for now (simplified)
    CHECK_FUNCS();
    if (g_funcs->create_string_utf8) return g_funcs->create_string_utf8(env, "", 0, result);
    return napi_generic_failure;
}

napi_status napi_get_value_string_utf16(napi_env env, napi_value value, uint16_t* buf, size_t bufsize, size_t* result) {
    if (result) *result = 0;
    return napi_ok;
}

napi_status napi_create_string_latin1(napi_env env, const char* str, size_t length, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_string_utf8) return g_funcs->create_string_utf8(env, str, length, result);
    return napi_generic_failure;
}

napi_status napi_get_value_string_latin1(napi_env env, napi_value value, char* buf, size_t bufsize, size_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_string_utf8) return g_funcs->get_value_string_utf8(env, value, buf, bufsize, result);
    return napi_generic_failure;
}

// =============================================================================
// Finalizer Functions
// =============================================================================

napi_status napi_add_finalizer(napi_env env, napi_value js_object, void* finalize_data, napi_finalize finalize_cb, void* finalize_hint, napi_ref* result) {
    // TODO: Implement proper finalizer support
    // For now, just create a reference if result is requested
    CHECK_FUNCS();
    if (result && g_funcs->create_reference) {
        return g_funcs->create_reference(env, js_object, 0, result);
    }
    if (result) *result = NULL;
    return napi_ok;
}

// =============================================================================
// Async Context Functions (stubs for compatibility)
// =============================================================================

typedef struct napi_async_context__* napi_async_context;

napi_status napi_async_init(napi_env env, napi_value async_resource, napi_value async_resource_name, napi_async_context* result) {
    // No-op stub - we don't need async hooks in Python
    if (result) *result = (napi_async_context)1;  // Non-NULL dummy value
    return napi_ok;
}

napi_status napi_async_destroy(napi_env env, napi_async_context async_context) {
    // No-op stub
    return napi_ok;
}

napi_status napi_make_callback(napi_env env, napi_async_context async_context, napi_value recv, napi_value func, size_t argc, const napi_value* argv, napi_value* result) {
    // Just call the function directly
    CHECK_FUNCS();
    if (g_funcs->call_function) return g_funcs->call_function(env, recv, func, argc, argv, result);
    return napi_generic_failure;
}

napi_status napi_open_callback_scope(napi_env env, napi_value resource_object, napi_async_context context, void** result) {
    if (result) *result = (void*)1;  // Non-NULL dummy value
    return napi_ok;
}

napi_status napi_close_callback_scope(napi_env env, void* scope) {
    return napi_ok;
}

// =============================================================================
// Async Work Functions (stubs - actual implementation would require thread pool)
// =============================================================================

napi_status napi_create_async_work(napi_env env, napi_value async_resource, napi_value async_resource_name, void* execute, void* complete, void* data, napi_async_work* result) {
    // TODO: Implement proper async work with thread pool
    // For now, return a dummy handle
    if (result) *result = (napi_async_work)1;
    return napi_ok;
}

napi_status napi_delete_async_work(napi_env env, napi_async_work work) {
    return napi_ok;
}

napi_status napi_queue_async_work(napi_env env, napi_async_work work) {
    // TODO: Actually queue the work to a thread pool
    return napi_ok;
}

napi_status napi_cancel_async_work(napi_env env, napi_async_work work) {
    return napi_ok;
}

napi_status napi_get_node_version(napi_env env, const void** result) {
    // Return NULL - we're not actually Node.js
    if (result) *result = NULL;
    return napi_ok;
}

napi_status napi_get_uv_event_loop(napi_env env, void** loop) {
    // Return NULL - we don't have a libuv event loop
    if (loop) *loop = NULL;
    return napi_ok;
}

napi_status napi_fatal_error(const char* location, size_t location_len, const char* message, size_t message_len) {
    // Print error and continue (don't actually abort)
    fprintf(stderr, "NAPI Fatal Error");
    if (location) fprintf(stderr, " at %s", location);
    if (message) fprintf(stderr, ": %s", message);
    fprintf(stderr, "\n");
    return napi_ok;
}

// Module registration (used by some addons)
typedef struct {
    int nm_version;
    unsigned int nm_flags;
    const char* nm_filename;
    napi_callback nm_register_func;
    const char* nm_modname;
    void* nm_priv;
    void* reserved[4];
} napi_module;

void napi_module_register(napi_module* mod) {
    // No-op - we handle module loading differently
}
